import os
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, disconnect
from flask_cors import CORS
from dotenv import load_dotenv
import logging
import asyncio
import json
from threading import Thread
from bs4 import BeautifulSoup
import re
import requests
import tiktoken

# =================================================================
# CONTEXT OPTIMIZATION CONFIGURATION
# =================================================================

# Conversation history limits
MAX_HISTORY_MESSAGES = 10  # Maximum messages to send to API (5 user + 5 assistant)
MEMORY_MESSAGES = 30  # Total messages to keep in memory/database

# DOM content limits
MAX_DOM_ELEMENTS = 50  # Maximum interactive elements to include
MAX_DOM_DEPTH = 3  # Maximum DOM tree depth
MAX_TEXT_LENGTH = 100  # Maximum text length per element
MAX_CLASSES_PER_ELEMENT = 3  # Maximum CSS classes to keep

# Token limits and warnings
MAX_TOKENS_PER_REQUEST = 120000  # Reduced from model limit for safety buffer
WARN_TOKENS_THRESHOLD = 100000  # Warn user when approaching limit

# Enable/disable optimizations
ENABLE_AGGRESSIVE_DOM_COMPRESSION = True
ENABLE_HISTORY_TRIMMING = True
ENABLE_TOKEN_COUNTING = True

# Import deep agent system
from langchain_core.messages import HumanMessage, AIMessage
from agents.deep_agent import agent, set_websocket_callback
from agents.google_tools import set_google_access_token
from conversation_db import get_conversation_db

# Initialize tokenizer for counting
try:
    tokenizer = tiktoken.encoding_for_model("gpt-4")
except:
    tokenizer = tiktoken.get_encoding("cl100k_base")

def count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken"""
    try:
        return len(tokenizer.encode(str(text)))
    except:
        # Fallback: rough estimate (4 chars ≈ 1 token)
        return len(str(text)) // 4

def estimate_messages_tokens(messages: list) -> int:
    """Estimate total tokens in message list"""
    total = 0
    for msg in messages:
        if isinstance(msg, dict):
            total += count_tokens(msg.get('content', ''))
        elif hasattr(msg, 'content'):
            total += count_tokens(msg.content)
        else:
            total += count_tokens(str(msg))
    return total

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Enable CORS for the extension
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize SocketIO with proper configuration
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',
    ping_timeout=60,
    ping_interval=25,
    logger=True,
    engineio_logger=True
)

api_key = os.getenv("GROQ_API_KEY")

# OAuth credentials
CLIENT_ID = "95116700360-13ege5jmfrjjt4vmd86oh00eu5jlei5e.apps.googleusercontent.com"
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")

# Track connected clients and their pending tool calls
connected_clients = {}  # {client_id: {"sid": sid, "pending_tool_calls": {}}}

# Track active agent execution threads
active_agent_threads = {}  # {client_id: {"thread": thread, "stop_flag": bool}}

# Map Socket.IO session IDs to persistent user IDs
sid_to_user_id = {}  # {sid: user_id}

# Initialize conversation database
conversation_db = get_conversation_db()


# =================================================================
# OAuth & Authentication Endpoints
# =================================================================

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'message': 'Backend service running'})

@app.route('/exchange-code', methods=['POST']) 
def exchange_code():
    """Exchange authorization code for access + refresh tokens"""
    data = request.json
    code = data.get('code')
    redirect_uri = data.get('redirect_uri')
    
    if not code or not redirect_uri:
        return jsonify({'error': 'Missing code or redirect_uri'}), 400
    
    try:
        response = requests.post(
            'https://oauth2.googleapis.com/token',
            data={
                'code': code,
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code'
            },
            timeout=10
        )
        
        if response.status_code != 200:
            return jsonify({
                'error': 'Token exchange failed',
                'details': response.text
            }), response.status_code
        
        token_data = response.json()
        return jsonify({
            'access_token': token_data.get('access_token'),
            'refresh_token': token_data.get('refresh_token'),
            'expires_in': token_data.get('expires_in', 3600),
            'token_type': token_data.get('token_type')
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/refresh-token', methods=['POST'])  
def refresh_token():
    """Get new access token using refresh token"""
    data = request.json
    refresh_token_value = data.get('refresh_token')
    
    if not refresh_token_value:
        return jsonify({'error': 'Missing refresh_token'}), 400
    
    try:
        response = requests.post(
            'https://oauth2.googleapis.com/token',
            data={
                'refresh_token': refresh_token_value,
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'grant_type': 'refresh_token'
            },
            timeout=10
        )
        
        if response.status_code != 200:
            return jsonify({
                'error': 'Token refresh failed',
                'details': response.text
            }), response.status_code
        
        token_data = response.json()
        return jsonify({
            'access_token': token_data.get('access_token'),
            'expires_in': token_data.get('expires_in', 3600),
            'token_type': token_data.get('token_type')
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/github/exchange-code', methods=['POST'])
def github_exchange_code():
    """Exchange GitHub authorization code for access token"""
    data = request.json
    code = data.get('code')
    
    if not code:
        return jsonify({'error': 'Missing code'}), 400
    
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        return jsonify({'error': 'GitHub OAuth not configured'}), 500
    
    try:
        response = requests.post(
            'https://github.com/login/oauth/access_token',
            headers={'Accept': 'application/json'},
            data={
                'client_id': GITHUB_CLIENT_ID,
                'client_secret': GITHUB_CLIENT_SECRET,
                'code': code
            },
            timeout=10
        )
        
        if response.status_code != 200:
            return jsonify({
                'error': 'Token exchange failed',
                'details': response.text
            }), response.status_code
        
        token_data = response.json()
        
        if 'error' in token_data:
            return jsonify({
                'error': token_data.get('error_description', 'Token exchange failed')
            }), 400
        
        return jsonify({
            'access_token': token_data.get('access_token'),
            'token_type': token_data.get('token_type', 'bearer'),
            'scope': token_data.get('scope', '')
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500





# =================================================================
# WEBSOCKET EVENT HANDLERS
# =================================================================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    sid = request.sid  # type: ignore
    
    # Initialize with SID, will be updated when user_id is received
    connected_clients[sid] = {
        "sid": sid,
        "pending_tool_calls": {},
        "google_token": None,
        "conversation_history": []
    }
    
    logger.info(f"Client connected (SID): {sid}. Total clients: {len(connected_clients)}")
    
    emit('connection_established', {
        'status': 'connected',
        'client_id': sid,
        'message': 'WebSocket connection established successfully'
    })

@socketio.on('register_user_id')
def handle_register_user_id(data):
    """Register persistent user ID for this session"""
    sid = request.sid  # type: ignore
    user_id = data.get('user_id')
    
    if not user_id:
        logger.error("❌ No user_id provided")
        return
    
    # Map SID to user_id
    sid_to_user_id[sid] = user_id
    
    # Load conversation history from database (limited to MEMORY_MESSAGES)
    stored_history = conversation_db.get_history(user_id, limit=MEMORY_MESSAGES)
    conversation_history = [{"role": msg["role"], "content": msg["content"]} for msg in stored_history]
    
    if sid in connected_clients:
        connected_clients[sid]["conversation_history"] = conversation_history
    
    logger.info(f"✅ User registered: {user_id[:16]}... Loaded {len(conversation_history)}/{MEMORY_MESSAGES} messages")
    
    emit('user_registered', {
        'ok': True,
        'user_id': user_id,
        'history_loaded': len(conversation_history),
        'max_history': MEMORY_MESSAGES
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    sid = request.sid  # type: ignore
    user_id = sid_to_user_id.get(sid)
    
    if sid in connected_clients:
        del connected_clients[sid]
    if sid in sid_to_user_id:
        del sid_to_user_id[sid]
    
    logger.info(f"Client disconnected (SID: {sid[:8]}..., User: {user_id[:16] if user_id else 'unknown'}...). Total clients: {len(connected_clients)}")

@socketio.on('ping')
def handle_ping(data):
    """Handle ping from client to keep connection alive"""
    emit('pong', {'timestamp': data.get('timestamp'), 'server_time': os.times().elapsed})

@socketio.on('set_google_token')
def handle_set_google_token(data):
    """Set Google access token for the connected client"""
    client_id = request.sid  # type: ignore
    access_token = data.get('access_token')
    
    if not access_token:
        emit('token_error', {'error': 'Missing access_token'})
        return
    
    try:
        # Store token in client data
        if client_id in connected_clients:
            connected_clients[client_id]["google_token"] = access_token
            # Set token for Google tools
            set_google_access_token(access_token)
            logger.info(f"✅ Google access token set for client {client_id}")
            emit('token_set', {'ok': True, 'message': 'Google token configured successfully'})
        else:
            emit('token_error', {'error': 'Client not found'})
    except Exception as e:
        logger.error(f"Error setting Google token: {str(e)}")
        emit('token_error', {'error': str(e)})

@socketio.on('clear_conversation_history')
def handle_clear_conversation_history():
    """Clear conversation history for the connected client"""
    client_id = request.sid  # type: ignore
    
    try:
        if client_id in connected_clients:
            # Clear from memory
            connected_clients[client_id]["conversation_history"] = []
            # Clear from database
            conversation_db.clear_history(client_id)
            logger.info(f"✅ Conversation history cleared for client {client_id}")
            emit('conversation_cleared', {'ok': True, 'message': 'Conversation history cleared successfully'})
        else:
            emit('clear_error', {'error': 'Client not found'})
    except Exception as e:
        logger.error(f"Error clearing conversation history: {str(e)}")
        emit('clear_error', {'error': str(e)})

@socketio.on('get_conversation_history')
def handle_get_conversation_history():
    """Get conversation history for the connected client"""
    client_id = request.sid  # type: ignore
    
    try:
        if client_id in connected_clients:
            # Get from database with full metadata
            history = conversation_db.get_history(client_id, limit=100)
            stats = conversation_db.get_client_stats(client_id)
            emit('conversation_history', {
                'ok': True, 
                'history': history, 
                'count': len(history),
                'stats': stats
            })
        else:
            emit('history_error', {'error': 'Client not found'})
    except Exception as e:
        logger.error(f"Error getting conversation history: {str(e)}")
        emit('history_error', {'error': str(e)})



# =================================================================
# AGENT TOOL EXECUTION HANDLERS
# =================================================================

def optimize_dom_data(result: dict) -> dict:
    """Aggressively compress DOM data to prevent context limit issues"""
    if not isinstance(result, dict) or not result.get('success'):
        return result
    
    data = result.get('data')
    if not data:
        return result
    
    # Check if this is DOM-related data
    is_dom_data = False
    if isinstance(data, dict):
        if 'tag' in data or 'children' in data or 'interactive' in data:
            is_dom_data = True
    elif isinstance(data, str):
        if '<html' in data.lower() or '<body' in data.lower() or '<div' in data.lower():
            is_dom_data = True
    
    if not is_dom_data:
        return result
    
    original_size = len(json.dumps(result))
    original_tokens = count_tokens(json.dumps(result))
    
    logger.info(f"🔬 Compressing DOM: {original_size} bytes, ~{original_tokens} tokens")
    
    try:
        if ENABLE_AGGRESSIVE_DOM_COMPRESSION:
            optimized_data = compress_dom_structure(data)
            result['data'] = optimized_data
        
        new_size = len(json.dumps(result))
        new_tokens = count_tokens(json.dumps(result))
        reduction = ((original_tokens - new_tokens) / original_tokens * 100) if original_tokens > 0 else 0
        
        logger.info(f"✅ DOM compressed: {original_tokens} → {new_tokens} tokens ({reduction:.1f}% reduction)")
        
        # If still too large, apply emergency truncation
        if new_tokens > 5000:
            logger.warning(f"⚠️ DOM still too large ({new_tokens} tokens), applying emergency truncation")
            result['data'] = emergency_truncate_dom(result['data'])
            final_tokens = count_tokens(json.dumps(result))
            logger.info(f"✅ Emergency truncation: {new_tokens} → {final_tokens} tokens")
        
    except Exception as e:
        logger.warning(f"⚠️ DOM optimization failed: {e}, applying safe fallback")
        result['data'] = emergency_truncate_dom(data)
    
    return result

def emergency_truncate_dom(data) -> dict:
    """Emergency DOM truncation when all else fails"""
    if isinstance(data, str):
        soup = BeautifulSoup(data[:10000], 'html.parser')  # Only parse first 10KB
        return compress_html_string(str(soup))
    elif isinstance(data, dict):
        return {
            'tag': data.get('tag', 'unknown'),
            'id': data.get('id'),
            'class': str(data.get('class', ''))[:50],
            'text': str(data.get('text', ''))[:100],
            'interactive_summary': f"{len(data.get('interactive', []))} interactive elements found",
            'note': 'DOM heavily truncated to prevent context overflow'
        }
    else:
        return {'truncated': True, 'type': str(type(data))}

def compress_dom_structure(data):
    """Compress DOM structure intelligently"""
    if isinstance(data, dict):
        return compress_dom_dict(data)
    elif isinstance(data, str):
        return compress_html_string(data)
    elif isinstance(data, list):
        return [compress_dom_structure(item) for item in data[:50]]  # Limit list size
    else:
        return data

def compress_dom_dict(node: dict) -> dict:
    """Compress a DOM node dict while keeping essential info"""
    compressed = {}
    
    # Always keep these essential fields
    essential_fields = ['tag', 'id', 'name', 'type', 'placeholder', 'ariaLabel', 'role']
    # Only include href/src for interactive elements
    if node.get('tag') in ['a', 'img', 'iframe', 'form']:
        essential_fields.extend(['href', 'src', 'action'])
    
    for field in essential_fields:
        if field in node and node[field]:
            compressed[field] = node[field]
    
    # Handle class attribute - keep only meaningful classes
    if 'class' in node or 'className' in node:
        classes = node.get('class') or node.get('className', '')
        if classes:
            if isinstance(classes, str):
                class_list = classes.split()
                meaningful_classes = [c for c in class_list if is_meaningful_class(c)]
                if meaningful_classes:
                    compressed['class'] = ' '.join(meaningful_classes[:MAX_CLASSES_PER_ELEMENT])
    
    # Handle text - truncate aggressively
    if 'text' in node:
        text = node['text']
        if text and isinstance(text, str):
            text = text.strip()
            if text:
                # Use configured max length
                compressed['text'] = text[:MAX_TEXT_LENGTH] + ('...' if len(text) > MAX_TEXT_LENGTH else '')
    
    # Handle attributes - only keep interactive/semantic ones
    if 'attributes' in node and isinstance(node['attributes'], dict):
        important_attrs = {}
        for key, value in node['attributes'].items():
            if is_important_attribute(key, value):
                # Truncate long attribute values
                str_value = str(value)
                important_attrs[key] = str_value[:100] if len(str_value) > 100 else str_value
        if important_attrs:
            compressed['attrs'] = important_attrs
    
    # Handle children - recursively compress with strict limits
    if 'children' in node and isinstance(node['children'], list):
        # Only keep truly interactive or semantic children
        important_children = []
        for child in node['children'][:10]:  # REDUCED: Max 10 children per node
            if isinstance(child, dict):
                child_tag = child.get('tag', '')
                # Stricter filtering - only keep actionable elements
                if (child_tag in ['button', 'a', 'input', 'textarea', 'select', 'form'] or
                    (child.get('id') and child_tag in ['div', 'span', 'nav', 'main'])):
                    important_children.append(compress_dom_dict(child))
        
        if important_children:
            compressed['children'] = important_children
    
    # Handle interactive elements list
    if 'interactive' in node and isinstance(node['interactive'], list):
        compressed['interactive'] = [
            compress_interactive_element(elem) 
            for elem in node['interactive'][:MAX_DOM_ELEMENTS]  # Use configured limit
        ]
    
    return compressed

def compress_interactive_element(elem: dict) -> dict:
    """Compress interactive element info"""
    compressed = {}
    
    # Essential fields for element identification
    for field in ['tag', 'type', 'id', 'name', 'placeholder', 'ariaLabel']:
        if field in elem and elem[field]:
            compressed[field] = elem[field]
    
    # Simplified class
    if 'class' in elem:
        classes = elem['class']
        if isinstance(classes, str):
            class_list = classes.split()
            meaningful = [c for c in class_list if is_meaningful_class(c)]
            if meaningful:
                compressed['class'] = ' '.join(meaningful[:3])
    
    # Truncated text
    if 'text' in elem and elem['text']:
        text = elem['text'].strip()
        if text:
            compressed['text'] = text[:80] + ('...' if len(text) > 80 else '')
    
    return compressed

def compress_html_string(html: str) -> dict:
    """Parse and compress raw HTML string using BeautifulSoup"""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract meaningful content
        result = {
            'title': soup.title.string if soup.title else None,
            'interactive_elements': [],
            'text_content': [],
            'forms': []
        }
        
        # Find all interactive elements
        interactive_selectors = ['button', 'a', 'input', 'textarea', 'select', '[role="button"]', '[contenteditable="true"]']
        for selector in interactive_selectors:
            for elem in soup.select(selector)[:15]:  # Limit per type
                elem_info = {
                    'tag': elem.name,
                    'id': elem.get('id'),
                    'class': ' '.join([c for c in elem.get('class', []) if is_meaningful_class(c)][:3]),
                    'type': elem.get('type'),
                    'name': elem.get('name'),
                    'placeholder': elem.get('placeholder'),
                    'text': elem.get_text(strip=True)[:60]
                }
                # Remove None/empty values
                elem_info = {k: v for k, v in elem_info.items() if v}
                if elem_info:
                    result['interactive_elements'].append(elem_info)
        
        # Extract forms
        for form in soup.find_all('form')[:5]:
            form_info = {
                'id': form.get('id'),
                'action': form.get('action'),
                'method': form.get('method'),
                'inputs': []
            }
            
            for inp in form.find_all(['input', 'textarea', 'select'])[:10]:
                form_info['inputs'].append({
                    'type': inp.get('type'),
                    'name': inp.get('name'),
                    'id': inp.get('id'),
                    'placeholder': inp.get('placeholder')
                })
            
            result['forms'].append({k: v for k, v in form_info.items() if v})
        
        # Extract main text content (headings, paragraphs)
        for tag in soup.find_all(['h1', 'h2', 'h3', 'p'])[:20]:
            text = tag.get_text(strip=True)
            if text and len(text) > 10:
                result['text_content'].append({
                    'tag': tag.name,
                    'text': text[:100] + ('...' if len(text) > 100 else '')
                })
        
        return {k: v for k, v in result.items() if v}  # Remove empty fields
        
    except Exception as e:
        logger.error(f"Error parsing HTML: {e}")
        # Fallback: return truncated string
        return {'raw': html[:500] + '...' if len(html) > 500 else html}

def is_meaningful_class(class_name: str) -> bool:
    """Check if a CSS class is meaningful for LLM (not just layout/utility)"""
    if not class_name or len(class_name) < 2:
        return False
    
    # Skip common utility classes
    utility_patterns = [
        r'^(p|m|pt|pb|pl|pr|mt|mb|ml|mr|px|py|mx|my)-\d+$',  # Tailwind spacing
        r'^(w|h|min-w|min-h|max-w|max-h)-',  # Size utilities
        r'^(flex|grid|block|inline|hidden)',  # Layout utilities
        r'^(text|font|leading|tracking)-',  # Text utilities
        r'^(bg|border|rounded|shadow)-',  # Styling utilities
        r'^(absolute|relative|fixed|sticky)',  # Position utilities
        r'^(col-|row-|gap-|space-)',  # Grid utilities
    ]
    
    for pattern in utility_patterns:
        if re.match(pattern, class_name, re.IGNORECASE):
            return False
    
    # Keep semantic classes
    semantic_keywords = ['button', 'nav', 'menu', 'modal', 'dialog', 'form', 'input', 'submit', 'search', 
                         'header', 'footer', 'main', 'content', 'sidebar', 'active', 'selected', 'disabled',
                         'primary', 'secondary', 'login', 'signup', 'profile', 'settings', 'dropdown']
    
    class_lower = class_name.lower()
    for keyword in semantic_keywords:
        if keyword in class_lower:
            return True
    
    # Keep if it looks like a component name (CamelCase or kebab-case with meaning)
    if len(class_name) > 4 and ('-' in class_name or any(c.isupper() for c in class_name)):
        return True
    
    return False

def is_important_attribute(key: str, value) -> bool:
    """Check if an attribute is important for LLM understanding"""
    important_attrs = [
        'data-test', 'data-testid', 'data-cy', 'data-id', 'data-action',
        'aria-label', 'aria-describedby', 'role', 'title', 'alt',
        'href', 'src', 'action', 'method', 'target', 'rel',
        'name', 'id', 'type', 'value', 'placeholder', 'required',
        'disabled', 'readonly', 'checked', 'selected'
    ]
    
    key_lower = key.lower()
    
    # Check exact matches
    if key_lower in important_attrs:
        return True
    
    # Check prefixes
    if key_lower.startswith('data-') and len(key_lower) > 5:
        return True
    
    if key_lower.startswith('aria-'):
        return True
    
    return False

@socketio.on('execute_agent_ws')
def handle_execute_agent_ws(data):
    """Execute the LangChain agent with sophisticated tools"""
    goal = data.get('goal')
    sid = request.sid  # type: ignore
    user_id = sid_to_user_id.get(sid, sid)  # Fallback to SID if no user_id
    
    logger.info(f"\n{'='*80}")
    logger.info(f"🚀 AGENT EXECUTION STARTED")
    logger.info(f"Session ID: {sid[:8]}...")
    logger.info(f"User ID: {user_id[:16]}...")
    logger.info(f"Goal: {goal}")
    logger.info(f"{'='*80}\n")
    
    if not goal:
        logger.error("❌ Missing goal parameter")
        emit('agent_error', {'error': 'Missing "goal"'})
        return
    
    # Use SID for Socket.IO operations, user_id for database
    client_id = sid  # For Socket.IO emissions and connected_clients
    
    try:
        emit('agent_progress', {
            'status': 'initializing',
            'message': 'Starting agent execution...'
        })
        logger.info("📤 Sent 'initializing' progress update")
        
        # Set Google access token if available
        if client_id in connected_clients and connected_clients[client_id].get("google_token"):
            google_token = connected_clients[client_id]["google_token"]
            set_google_access_token(google_token)
            logger.info("✅ Google access token configured for agent tools")
        
        # Set up WebSocket callback for tool execution
        async def tool_callback(action_type: str, params: dict):
            """Callback function for tools to execute browser actions"""
            import uuid
            tool_id = str(uuid.uuid4())
            
            logger.info(f"\n{'='*60}")
            logger.info(f"🔧 TOOL CALLBACK TRIGGERED")
            logger.info(f"Tool ID: {tool_id}")
            logger.info(f"Action Type: {action_type}")
            logger.info(f"Params: {json.dumps(params, indent=2)}")
            logger.info(f"{'='*60}\n")
            
            # Store pending tool call
            if client_id in connected_clients:
                connected_clients[client_id]["pending_tool_calls"][tool_id] = {
                    "action_type": action_type,
                    "params": params,
                    "result": None,
                    "completed": False
                }
                logger.info(f"✅ Stored pending tool call for client {client_id}")
            else:
                logger.error(f"❌ Client {client_id} not found in connected_clients")
            
            # Send tool execution request to extension
            logger.info(f"📤 Sending tool_execution_request to extension...")
            socketio.emit('tool_execution_request', {
                'tool_id': tool_id,
                'action_type': action_type,
                'params': params
            }, to=client_id)
            logger.info(f"✅ Tool execution request sent")
            
            # Wait for result with timeout
            max_wait = 30  # 30 seconds timeout
            waited = 0
            logger.info(f"⏳ Waiting for tool result (timeout: {max_wait}s)...")
            
            while waited < max_wait:
                await asyncio.sleep(0.1)
                waited += 0.1
                
                if waited % 5 == 0:  # Log every 5 seconds
                    logger.info(f"⏱️  Still waiting... ({waited}s elapsed)")
                
                if client_id in connected_clients:
                    tool_call = connected_clients[client_id]["pending_tool_calls"].get(tool_id)
                    if tool_call and tool_call["completed"]:
                        result = tool_call["result"]
                        logger.info(f"✅ Tool result received after {waited:.1f}s")
                        
                        # Optimize DOM data if present
                        if action_type in ['GET_PAGE_INFO', 'EXTRACT_DOM', 'FIND_ELEMENTS']:
                            result = optimize_dom_data(result)
                        
                        logger.info(f"Result: {json.dumps(result, indent=2)[:500]}...")
                        # Clean up
                        del connected_clients[client_id]["pending_tool_calls"][tool_id]
                        return result
            
            # Timeout
            logger.error(f"⏰ Tool execution TIMEOUT after {max_wait}s")
            logger.error(f"Tool ID: {tool_id}, Action: {action_type}")
            return {"success": False, "error": "Tool execution timeout"}
        
        # Set the callback for agent tools
        set_websocket_callback(tool_callback)
        
        emit('agent_progress', {
            'status': 'planning',
            'message': 'Agent is analyzing the task and planning actions...'
        })
        
        # Execute agent in a separate thread to avoid blocking
        def run_agent():
            try:
                # Check if stop was requested (using user_id for thread tracking)
                if user_id in active_agent_threads and active_agent_threads[user_id].get("stop_flag"):
                    logger.info(f"🛑 Agent execution stopped before starting")
                    socketio.emit('agent_error', {'error': 'Agent execution stopped by user'}, to=client_id)
                    if user_id in active_agent_threads:
                        del active_agent_threads[user_id]
                    return
                
                logger.info(f"🤖 Invoking agent with goal: {goal}")
                
                # Get conversation history for this client
                conversation_history = []
                if client_id in connected_clients:
                    full_history = connected_clients[client_id].get("conversation_history", [])
                    
                    # Apply sliding window to limit context
                    if ENABLE_HISTORY_TRIMMING and len(full_history) > MAX_HISTORY_MESSAGES:
                        # Keep only recent messages
                        conversation_history = full_history[-MAX_HISTORY_MESSAGES:]
                        logger.info(f"📚 Trimmed history: {len(full_history)} → {len(conversation_history)} messages")
                    else:
                        conversation_history = full_history
                        logger.info(f"📚 Using {len(conversation_history)} messages from history")
                
                # Convert conversation history to LangChain message objects
                langchain_messages = []
                for msg in conversation_history:
                    if msg["role"] == "user":
                        langchain_messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        langchain_messages.append(AIMessage(content=msg["content"]))
                
                # Add the new user message
                langchain_messages.append(HumanMessage(content=goal))
                
                # Count tokens and warn if approaching limit
                if ENABLE_TOKEN_COUNTING:
                    total_tokens = estimate_messages_tokens(langchain_messages)
                    logger.info(f"📊 Estimated tokens: {total_tokens}")
                    
                    if total_tokens > WARN_TOKENS_THRESHOLD:
                        logger.warning(f"⚠️ HIGH TOKEN COUNT: {total_tokens} tokens (limit: {MAX_TOKENS_PER_REQUEST})")
                        socketio.emit('agent_warning', {
                            'type': 'high_token_count',
                            'tokens': total_tokens,
                            'limit': MAX_TOKENS_PER_REQUEST,
                            'message': f'Request is using {total_tokens} tokens, approaching limit'
                        }, to=client_id)
                    
                    if total_tokens > MAX_TOKENS_PER_REQUEST:
                        error_msg = f"Request exceeds token limit ({total_tokens} > {MAX_TOKENS_PER_REQUEST}). Try: 1) Clearing history 2) Shorter prompt 3) Asking about specific page sections"
                        logger.error(f"❌ {error_msg}")
                        socketio.emit('agent_error', {'error': error_msg}, to=client_id)
                        return
                
                logger.info(f"📨 Passing {len(langchain_messages)} messages to agent")
                
                # Stream agent execution with real-time updates
                socketio.emit('agent_progress', {
                    'status': 'executing',
                    'message': 'Agent is executing...',
                    'step': 'started'
                }, to=client_id)
                
                all_messages = []
                step_count = 0
                output = ""
                
                # Use agent.stream() with stream_mode="updates" for step-by-step progress
                for chunk in agent.stream(
                    {"messages": langchain_messages},
                    stream_mode="updates"
                ):
                    # Check if stop was requested during streaming
                    if user_id in active_agent_threads and active_agent_threads[user_id].get("stop_flag"):
                        logger.info(f"🛑 Agent execution stopped during streaming")
                        socketio.emit('agent_error', {'error': 'Agent execution stopped by user'}, to=client_id)
                        return
                    
                    # Each chunk contains updates from different nodes (model, tools, etc.)
                    for node_name, node_data in chunk.items():
                        step_count += 1
                        messages_in_step = node_data.get('messages', [])
                        
                        if messages_in_step:
                            last_message = messages_in_step[-1]
                            all_messages.extend(messages_in_step)
                            
                            # Determine the type of update
                            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                                # Agent is calling a tool
                                tool_names = [tc['name'] for tc in last_message.tool_calls]
                                logger.info(f"🔧 Step {step_count} [{node_name}]: Calling tools: {', '.join(tool_names)}")
                                socketio.emit('agent_progress', {
                                    'status': 'tool_calling',
                                    'message': f"Calling tools: {', '.join(tool_names)}",
                                    'step': step_count,
                                    'node': node_name,
                                    'tools': tool_names
                                }, to=client_id)
                            elif hasattr(last_message, 'content') and last_message.content:
                                # Agent/tool response
                                content = last_message.content
                                content_preview = content[:100] + "..." if len(content) > 100 else content
                                logger.info(f"💬 Step {step_count} [{node_name}]: {content_preview}")
                                socketio.emit('agent_progress', {
                                    'status': 'responding',
                                    'message': f"Step {step_count}: {content_preview}",
                                    'step': step_count,
                                    'node': node_name,
                                    'content': content
                                }, to=client_id)
                                
                                # Update output with latest content
                                if node_name == 'model' or node_name == 'agent':
                                    output = content
                
                logger.info(f"📥 Agent streaming completed")
                logger.info(f"Total steps: {step_count}")
                logger.info(f"Total messages: {len(all_messages)}")
                
                # Get final output
                if not output and all_messages:
                    final_message = all_messages[-1]
                    output = final_message.content if hasattr(final_message, 'content') else str(final_message)
                
                messages = all_messages
                
                # Store updated conversation history
                if client_id in connected_clients:
                    # Add to memory (keep last MEMORY_MESSAGES)
                    connected_clients[client_id]["conversation_history"].append({"role": "user", "content": goal})
                    connected_clients[client_id]["conversation_history"].append({"role": "assistant", "content": output})
                    
                    # Trim to memory limit
                    if len(connected_clients[client_id]["conversation_history"]) > MEMORY_MESSAGES:
                        connected_clients[client_id]["conversation_history"] = connected_clients[client_id]["conversation_history"][-MEMORY_MESSAGES:]
                    
                    # Save to database using persistent user_id
                    conversation_db.add_message(user_id, "user", goal, metadata={"steps": len(messages) - 1})
                    conversation_db.add_message(user_id, "assistant", output)
                    
                    current_count = len(connected_clients[client_id]['conversation_history'])
                    logger.info(f"💾 Stored conversation (user: {user_id[:16]}..., memory: {current_count}/{MEMORY_MESSAGES})")
                
                logger.info(f"✅ Agent execution completed successfully")
                logger.info(f"Final output: {output[:200]}..." if len(str(output)) > 200 else f"Final output: {output}")
                
                socketio.emit('agent_completed', {
                    'ok': True,
                    'result': output,
                    'steps_taken': step_count,
                    'total_messages': len(messages),
                    'history_count': len(connected_clients.get(client_id, {}).get("conversation_history", []))
                }, to=client_id)
                logger.info(f"📤 Sent 'agent_completed' event to client (steps: {step_count})")
                
            except Exception as e:
                logger.error(f"❌ Error in agent execution: {str(e)}")
                logger.error(f"Error type: {type(e).__name__}")
                import traceback
                logger.error(f"Traceback:\n{traceback.format_exc()}")
                socketio.emit('agent_error', {
                    'error': str(e)
                }, to=client_id)
            finally:
                # Clean up active thread tracking
                if user_id in active_agent_threads:
                    del active_agent_threads[user_id]
                    logger.info(f"🧹 Cleaned up agent thread for user {user_id[:16]}...")
        
        # Start agent execution in background
        thread = Thread(target=run_agent)
        active_agent_threads[user_id] = {"thread": thread, "stop_flag": False}
        thread.start()
        logger.info(f"🚀 Agent thread started for user {user_id[:16]}...")
        
    except Exception as e:
        logger.error(f"Error executing agent: {str(e)}")
        emit('agent_error', {'error': str(e)})

@socketio.on('tool_execution_result')
def handle_tool_execution_result(data):
    """Receive tool execution results from the extension"""
    tool_id = data.get('tool_id')
    result = data.get('result')
    client_id = request.sid  # type: ignore
    
    if not tool_id:
        logger.error("Missing tool_id in tool execution result")
        return
    
    # Update the pending tool call with result
    if client_id in connected_clients:
        if tool_id in connected_clients[client_id]["pending_tool_calls"]:
            connected_clients[client_id]["pending_tool_calls"][tool_id]["result"] = result
            connected_clients[client_id]["pending_tool_calls"][tool_id]["completed"] = True
            logger.info(f"Tool {tool_id} completed for client {client_id}")

@socketio.on('agent_feedback')
def handle_agent_feedback(data):
    """Receive feedback/status updates from extension during agent execution"""
    message = data.get('message')
    status = data.get('status', 'info')
    
    logger.info(f"Agent feedback [{status}]: {message}")
    
    # Broadcast to all clients or specific client if needed
    emit('agent_progress', {
        'status': status,
        'message': message,
        'timestamp': data.get('timestamp')
    })

@socketio.on('stop_agent_ws')
def handle_stop_agent_ws(data):
    """Stop the currently running agent execution"""
    sid = request.sid  # type: ignore
    user_id = sid_to_user_id.get(sid, sid)  # Fallback to SID
    
    logger.info(f"\n{'='*80}")
    logger.info(f"🛑 STOP AGENT REQUEST RECEIVED")
    logger.info(f"Session ID: {sid[:8]}...")
    logger.info(f"User ID: {user_id[:16]}...")
    logger.info(f"{'='*80}\n")
    
    try:
        if user_id in active_agent_threads:
            # Set the stop flag
            active_agent_threads[user_id]["stop_flag"] = True
            logger.info(f"✅ Stop flag set for user {user_id[:16]}...")
            
            # Notify the client
            emit('agent_stopped', {
                'ok': True,
                'message': 'Agent execution stop requested'
            })
            logger.info(f"📤 Sent 'agent_stopped' event to client")
            
            # Clean up pending tool calls
            if sid in connected_clients:
                connected_clients[sid]["pending_tool_calls"] = {}
                logger.info(f"🧹 Cleared pending tool calls for session {sid[:8]}...")
        else:
            logger.warning(f"⚠️ No active agent execution found for user {user_id[:16]}...")
            emit('agent_stopped', {
                'ok': False,
                'message': 'No active agent execution to stop'
            })
    
    except Exception as e:
        logger.error(f"❌ Error stopping agent: {str(e)}")
        emit('agent_error', {'error': f'Error stopping agent: {str(e)}'})

# =================================================================
# MAIN
# ==================================================================

if __name__ == "__main__":
    logger.info("="*60)
    logger.info("🚀 Starting Unified Backend Server")
    logger.info("="*60)
    
    # Check OAuth credentials
    if not CLIENT_SECRET:
        logger.warning("⚠️  GOOGLE_CLIENT_SECRET not set - Google OAuth disabled")
    else:
        logger.info("✅ Google OAuth configured")
    
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        logger.warning("⚠️  GITHUB credentials not set - GitHub OAuth disabled")
    else:
        logger.info("✅ GitHub OAuth configured")
    
    if not api_key:
        logger.warning("⚠️  GROQ_API_KEY not set - Agent features may be limited")
    else:
        logger.info("✅ Groq AI configured")
    
    logger.info("✅ SQLite conversation database initialized")
    
    logger.info("")
    logger.info("📡 Server endpoints:")
    logger.info("   HTTP/REST: http://0.0.0.0:8080")
    logger.info("   WebSocket: ws://0.0.0.0:8080/socket.io/")
    logger.info("   OAuth: /exchange-code, /refresh-token, /github/exchange-code")
    logger.info("   Agent: WebSocket only (execute_agent_ws)")
    logger.info("   Features: Persistent conversation history (SQLite, auto-restored)")
    logger.info("="*60)
    
    # Run with SocketIO instead of Flask's run
    socketio.run(
        app,
        host="0.0.0.0",
        port=8080,
        debug=True,
        allow_unsafe_werkzeug=True
    )
