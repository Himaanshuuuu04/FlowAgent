import os
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, disconnect
from flask_cors import CORS
from dotenv import load_dotenv
import logging

from langchain_groq import ChatGroq
from generator.prompt import SCRIPT_PROMPT
from generator.sanitize import sanitize_json_actions
from generator.conversation_manager import ConversationManager

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

# Track connected clients
connected_clients = set()

# Initialize LangChain Groq Model
llm = ChatGroq(
    api_key=api_key,
    model="openai/gpt-oss-120b",  # or any Groq LLM you want
    temperature=0.2,
)

# Initialize Conversation Manager
conversation_manager = ConversationManager()


@app.route("/generate-script", methods=["POST"])
def generate_script():
    data = request.get_json() or {}
    goal = data.get("goal")
    target_url = data.get("target_url", "")
    dom_structure = data.get("dom_structure", {})
    constraints = data.get("constraints", {})

    if not goal:
        return jsonify({"error": "Missing 'goal'"}), 400

    try:
        # Get relevant context from past interactions
        relevant_context = conversation_manager.get_relevant_context(
            goal=goal,
            target_url=target_url,
            k=3  # Get top 3 similar interactions
        )
        
        # Format DOM structure for the prompt
        dom_info = ""
        if dom_structure:
            dom_info = f"\n\n=== PAGE INFORMATION ===\n"
            dom_info += f"URL: {dom_structure.get('url', target_url)}\n"
            dom_info += f"Title: {dom_structure.get('title', 'Unknown')}\n\n"
            
            interactive = dom_structure.get('interactive', [])
            if interactive:
                dom_info += f"=== INTERACTIVE ELEMENTS ({len(interactive)} found) ===\n"
                for i, elem in enumerate(interactive[:30], 1):  # Limit to 30 to avoid token limits
                    dom_info += f"\n{i}. {elem.get('tag', 'unknown')}"
                    if elem.get('id'):
                        dom_info += f" id=\"{elem['id']}\""
                    if elem.get('class'):
                        dom_info += f" class=\"{elem['class']}\""
                    if elem.get('type'):
                        dom_info += f" type=\"{elem['type']}\""
                    if elem.get('placeholder'):
                        dom_info += f" placeholder=\"{elem['placeholder']}\""
                    if elem.get('name'):
                        dom_info += f" name=\"{elem['name']}\""
                    if elem.get('ariaLabel'):
                        dom_info += f" aria-label=\"{elem['ariaLabel']}\""
                    if elem.get('text'):
                        dom_info += f"\n   Text: {elem['text'][:80]}"
                dom_info += "\n"

        # Format context from similar past interactions
        context_info = conversation_manager.format_context_for_prompt(relevant_context)

        user_prompt = (
            f"Goal: {goal}\n"
            f"Target URL: {target_url}\n"
            f"Constraints: {constraints}"
            f"{context_info}"
            f"{dom_info}\n\n"
            "IMPORTANT: Analyze the goal carefully:\n"
            "- If the goal involves opening/closing/switching tabs or navigating to URLs, use TAB CONTROL actions\n"
            "- If the goal involves interacting with page elements (clicking, typing), use DOM actions\n"
            "- If the goal requires both (e.g., 'open new tab and search'), combine both action types\n\n"
            "⚠️ CRITICAL FOR SEARCHES:\n"
            "- When user wants to 'search for X' or 'open new tab and search for X':\n"
            "  → Use OPEN_TAB with the complete search URL (e.g., https://www.google.com/search?q=X)\n"
            "  → DO NOT open chrome://newtab or about:blank and then try to type - this FAILS\n"
            "  → Encode spaces in URL as '+' or '%20'\n"
            "- Only use TYPE/CLICK actions if the target is a real website (http/https), not chrome:// pages\n\n"
            "Based on the page structure and past successful interactions above, "
            "generate the most accurate JSON action plan."
        )

        # LangChain prompt → Groq LLM
        ai_response = SCRIPT_PROMPT | llm
        result = ai_response.invoke({"input": user_prompt}).content

        action_plan, problems = sanitize_json_actions(result)

        if problems:
            return jsonify({
                "ok": False,
                "error": "Action plan failed validation.",
                "problems": problems,
                "raw_response": result[:1000]
            }), 400

        # Store this interaction for future reference
        conversation_manager.add_interaction(
            goal=goal,
            target_url=target_url,
            dom_structure=dom_structure,
            action_plan=action_plan,
            result=None  # Will be updated later via /update-result endpoint
        )

        return jsonify({
            "ok": True,
            "action_plan": action_plan,
            "context_used": len(relevant_context) > 0,
            "similar_interactions": len(relevant_context)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/update-result", methods=["POST"])
def update_result():
    """Update the result of the last action plan execution"""
    data = request.get_json() or {}
    result = data.get("result", {})
    
    try:
        # Get the last interaction from current session
        session_history = conversation_manager.get_session_history()
        if session_history:
            last_interaction = session_history[-1]
            
            # Re-add with updated result
            conversation_manager.add_interaction(
                goal=last_interaction["goal"],
                target_url=last_interaction["target_url"],
                dom_structure={},  # Already stored
                action_plan=last_interaction["action_plan"],
                result=result
            )
        
        return jsonify({
            "ok": True,
            "message": "Result updated successfully"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/conversation-stats", methods=["GET"])
def get_conversation_stats():
    """Get statistics about conversation history"""
    try:
        stats = conversation_manager.get_statistics()
        return jsonify({
            "ok": True,
            "stats": stats
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/clear-session", methods=["POST"])
def clear_session():
    """Clear current session history"""
    try:
        conversation_manager.clear_session()
        return jsonify({
            "ok": True,
            "message": "Session cleared successfully"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =================================================================
# WEBSOCKET EVENT HANDLERS
# =================================================================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    client_id = request.sid
    connected_clients.add(client_id)
    logger.info(f"Client connected: {client_id}. Total clients: {len(connected_clients)}")
    
    emit('connection_established', {
        'status': 'connected',
        'client_id': client_id,
        'message': 'WebSocket connection established successfully'
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    client_id = request.sid
    connected_clients.discard(client_id)
    logger.info(f"Client disconnected: {client_id}. Total clients: {len(connected_clients)}")

@socketio.on('ping')
def handle_ping(data):
    """Handle ping from client to keep connection alive"""
    emit('pong', {'timestamp': data.get('timestamp'), 'server_time': os.times().elapsed})

@socketio.on('generate_script_ws')
def handle_generate_script_ws(data):
    """WebSocket version of generate-script endpoint"""
    goal = data.get('goal')
    target_url = data.get('target_url', '')
    dom_structure = data.get('dom_structure', {})
    constraints = data.get('constraints', {})
    
    if not goal:
        emit('script_error', {'error': 'Missing "goal"'})
        return
    
    try:
        # Send progress update
        emit('script_progress', {'status': 'analyzing', 'message': 'Analyzing request...'})
        
        # Get relevant context from past interactions
        relevant_context = conversation_manager.get_relevant_context(
            goal=goal,
            target_url=target_url,
            k=3
        )
        
        emit('script_progress', {'status': 'extracting_dom', 'message': 'Processing page structure...'})
        
        # Format DOM structure for the prompt
        dom_info = ""
        if dom_structure:
            dom_info = f"\n\n=== PAGE INFORMATION ===\n"
            dom_info += f"URL: {dom_structure.get('url', target_url)}\n"
            dom_info += f"Title: {dom_structure.get('title', 'Unknown')}\n\n"
            
            interactive = dom_structure.get('interactive', [])
            if interactive:
                dom_info += f"=== INTERACTIVE ELEMENTS ({len(interactive)} found) ===\n"
                for i, elem in enumerate(interactive[:30], 1):
                    dom_info += f"\n{i}. {elem.get('tag', 'unknown')}"
                    if elem.get('id'):
                        dom_info += f" id=\"{elem['id']}\""
                    if elem.get('class'):
                        dom_info += f" class=\"{elem['class']}\""
                    if elem.get('type'):
                        dom_info += f" type=\"{elem['type']}\""
                    if elem.get('placeholder'):
                        dom_info += f" placeholder=\"{elem['placeholder']}\""
                    if elem.get('name'):
                        dom_info += f" name=\"{elem['name']}\""
                    if elem.get('ariaLabel'):
                        dom_info += f" aria-label=\"{elem['ariaLabel']}\""
                    if elem.get('text'):
                        dom_info += f"\n   Text: {elem['text'][:80]}"
                dom_info += "\n"
        
        emit('script_progress', {'status': 'generating', 'message': 'Generating action plan...'})
        
        # Format context from similar past interactions
        context_info = conversation_manager.format_context_for_prompt(relevant_context)
        
        user_prompt = (
            f"Goal: {goal}\n"
            f"Target URL: {target_url}\n"
            f"Constraints: {constraints}"
            f"{context_info}"
            f"{dom_info}\n\n"
            "IMPORTANT: Analyze the goal carefully:\n"
            "- If the goal involves opening/closing/switching tabs or navigating to URLs, use TAB CONTROL actions\n"
            "- If the goal involves interacting with page elements (clicking, typing), use DOM actions\n"
            "- If the goal requires both (e.g., 'open new tab and search'), combine both action types\n\n"
            "⚠️ CRITICAL FOR SEARCHES:\n"
            "- When user wants to 'search for X' or 'open new tab and search for X':\n"
            "  → Use OPEN_TAB with the complete search URL (e.g., https://www.google.com/search?q=X)\n"
            "  → DO NOT open chrome://newtab or about:blank and then try to type - this FAILS\n"
            "  → Encode spaces in URL as '+' or '%20'\n"
            "- Only use TYPE/CLICK actions if the target is a real website (http/https), not chrome:// pages\n\n"
            "Based on the page structure and past successful interactions above, "
            "generate the most accurate JSON action plan."
        )
        
        # LangChain prompt → Groq LLM
        ai_response = SCRIPT_PROMPT | llm
        result = ai_response.invoke({"input": user_prompt}).content
        
        emit('script_progress', {'status': 'validating', 'message': 'Validating action plan...'})
        
        action_plan, problems = sanitize_json_actions(result)
        
        if problems:
            emit('script_error', {
                'error': 'Action plan failed validation.',
                'problems': problems,
                'raw_response': result[:1000]
            })
            return
        
        # Store this interaction for future reference
        conversation_manager.add_interaction(
            goal=goal,
            target_url=target_url,
            dom_structure=dom_structure,
            action_plan=action_plan,
            result=None
        )
        
        emit('script_generated', {
            'ok': True,
            'action_plan': action_plan,
            'context_used': len(relevant_context) > 0,
            'similar_interactions': len(relevant_context)
        })
        
    except Exception as e:
        logger.error(f"Error generating script: {str(e)}")
        emit('script_error', {'error': str(e)})

@socketio.on('update_result_ws')
def handle_update_result_ws(data):
    """WebSocket version of update-result endpoint"""
    result = data.get('result', {})
    
    try:
        session_history = conversation_manager.get_session_history()
        if session_history:
            last_interaction = session_history[-1]
            
            conversation_manager.add_interaction(
                goal=last_interaction["goal"],
                target_url=last_interaction["target_url"],
                dom_structure={},
                action_plan=last_interaction["action_plan"],
                result=result
            )
        
        emit('result_updated', {
            'ok': True,
            'message': 'Result updated successfully'
        })
    except Exception as e:
        logger.error(f"Error updating result: {str(e)}")
        emit('update_error', {'error': str(e)})

@socketio.on('get_stats_ws')
def handle_get_stats_ws():
    """WebSocket version of conversation-stats endpoint"""
    try:
        stats = conversation_manager.get_statistics()
        emit('stats_response', {
            'ok': True,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        emit('stats_error', {'error': str(e)})

# =================================================================
# MAIN
# =================================================================

if __name__ == "__main__":
    logger.info("Starting Flask-SocketIO server...")
    logger.info(f"Server will be available at http://0.0.0.0:8080")
    logger.info(f"WebSocket endpoint: ws://0.0.0.0:8080/socket.io/")
    
    # Run with SocketIO instead of Flask's run
    socketio.run(
        app,
        host="0.0.0.0",
        port=8080,
        debug=True,
        allow_unsafe_werkzeug=True
    )
