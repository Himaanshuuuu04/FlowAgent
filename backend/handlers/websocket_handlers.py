"""WebSocket event handlers for real-time communication"""
import os
import logging
import asyncio
import json
from threading import Thread
from flask import request
from flask_socketio import emit
from langchain_core.messages import HumanMessage, AIMessage

from config.settings import (
    MAX_HISTORY_MESSAGES, MEMORY_MESSAGES, 
    ENABLE_HISTORY_TRIMMING, ENABLE_TOKEN_COUNTING,
    MAX_TOKENS_PER_REQUEST, WARN_TOKENS_THRESHOLD
)
from utils.token_utils import estimate_messages_tokens
from agents.deep_agent import agent, set_websocket_callback
from agents.google_tools import set_google_access_token

logger = logging.getLogger(__name__)

# Track connected clients and their pending tool calls
connected_clients = {}  # {client_id: {"sid": sid, "pending_tool_calls": {}}}

# Track active agent execution threads
active_agent_threads = {}  # {client_id: {"thread": thread, "stop_flag": bool}}

# Map Socket.IO session IDs to persistent user IDs
sid_to_user_id = {}  # {sid: user_id}

# Will be set by server.py
conversation_db = None
socketio = None


def init_handlers(sio, db):
    """Initialize handlers with socketio and database instances"""
    global socketio, conversation_db
    socketio = sio
    conversation_db = db


def register_handlers(sio):
    """Register all WebSocket event handlers"""
    
    @sio.on('connect')
    def handle_connect():
        """Handle client connection"""
        sid = request.sid
        
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

    @sio.on('register_user_id')
    def handle_register_user_id(data):
        """Register persistent user ID for this session"""
        sid = request.sid
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

    @sio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        sid = request.sid
        user_id = sid_to_user_id.get(sid)
        
        if sid in connected_clients:
            del connected_clients[sid]
        if sid in sid_to_user_id:
            del sid_to_user_id[sid]
        
        logger.info(f"Client disconnected (SID: {sid[:8]}..., User: {user_id[:16] if user_id else 'unknown'}...). Total clients: {len(connected_clients)}")

    @sio.on('ping')
    def handle_ping(data):
        """Handle ping from client to keep connection alive"""
        emit('pong', {'timestamp': data.get('timestamp'), 'server_time': os.times().elapsed})

    @sio.on('set_google_token')
    def handle_set_google_token(data):
        """Set Google access token for the connected client"""
        client_id = request.sid
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

    @sio.on('clear_conversation_history')
    def handle_clear_conversation_history():
        """Clear conversation history for the connected client"""
        client_id = request.sid
        
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

    @sio.on('get_conversation_history')
    def handle_get_conversation_history():
        """Get conversation history for the connected client"""
        client_id = request.sid
        
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

    @sio.on('execute_agent_ws')
    def handle_execute_agent_ws(data):
        """Execute the LangChain agent with sophisticated tools"""
        goal = data.get('goal')
        sid = request.sid
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
                    # Check if stop was requested
                    if user_id in active_agent_threads and active_agent_threads[user_id].get("stop_flag"):
                        logger.info(f"🛑 Tool execution stopped by user (tool: {action_type})")
                        return {"success": False, "error": "Agent execution stopped by user", "stopped": True}
                    
                    await asyncio.sleep(0.1)
                    waited += 0.1
                    
                    if waited % 5 == 0:  # Log every 5 seconds
                        logger.info(f"⏱️  Still waiting... ({waited}s elapsed)")
                    
                    if client_id in connected_clients:
                        tool_call = connected_clients[client_id]["pending_tool_calls"].get(tool_id)
                        if tool_call and tool_call["completed"]:
                            result = tool_call["result"]
                            logger.info(f"✅ Tool result received after {waited:.1f}s")
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
                    # Configure with recursion limit to prevent infinite loops
                    stream_config = {
                        "recursion_limit": 50,  # Prevent infinite loops in subagents
                    }
                    
                    for chunk in agent.stream(
                        {"messages": langchain_messages},
                        stream_mode="updates",
                        config=stream_config
                    ):
                        # Check if stop was requested during streaming (check frequently)
                        if user_id in active_agent_threads and active_agent_threads[user_id].get("stop_flag"):
                            logger.info(f"🛑 Agent execution stopped during streaming (deep agent + all subagents)")
                            socketio.emit('agent_stopped', {
                                'ok': True,
                                'message': 'Agent execution stopped by user',
                                'stopped_at': f'step {step_count}'
                            }, to=client_id)
                            # Clean up
                            if user_id in active_agent_threads:
                                del active_agent_threads[user_id]
                            return
                        
                        # Each chunk contains updates from different nodes (model, tools, etc.)
                        for node_name, node_data in chunk.items():
                            # Check stop flag before processing each node
                            if user_id in active_agent_threads and active_agent_threads[user_id].get("stop_flag"):
                                logger.info(f"🛑 Agent stopped before processing node: {node_name}")
                                socketio.emit('agent_stopped', {
                                    'ok': True,
                                    'message': 'Agent execution stopped by user',
                                    'stopped_at': f'node {node_name}'
                                }, to=client_id)
                                if user_id in active_agent_threads:
                                    del active_agent_threads[user_id]
                                return
                            
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

    @sio.on('tool_execution_result')
    def handle_tool_execution_result(data):
        """Receive tool execution results from the extension"""
        tool_id = data.get('tool_id')
        result = data.get('result')
        client_id = request.sid
        
        if not tool_id:
            logger.error("Missing tool_id in tool execution result")
            return
        
        # Update the pending tool call with result
        if client_id in connected_clients:
            if tool_id in connected_clients[client_id]["pending_tool_calls"]:
                connected_clients[client_id]["pending_tool_calls"][tool_id]["result"] = result
                connected_clients[client_id]["pending_tool_calls"][tool_id]["completed"] = True
                logger.info(f"Tool {tool_id} completed for client {client_id}")

    @sio.on('agent_feedback')
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

    @sio.on('stop_agent_ws')
    def handle_stop_agent_ws(data):
        """Stop the currently running agent execution"""
        sid = request.sid
        user_id = sid_to_user_id.get(sid, sid)  # Fallback to SID
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🛑 STOP AGENT REQUEST RECEIVED")
        logger.info(f"Session ID: {sid[:8]}...")
        logger.info(f"User ID: {user_id[:16]}...")
        logger.info(f"{'='*80}\n")
        
        try:
            if user_id in active_agent_threads:
                # Set the stop flag - this will interrupt deep agent and all subagents
                active_agent_threads[user_id]["stop_flag"] = True
                logger.info(f"✅ Stop flag set for user {user_id[:16]}...")
                logger.info(f"🛑 Stopping: Deep agent + all subagents (page-analyzer, interactor, navigator, data-manager, synchronizer)")
                
                # Clean up pending tool calls immediately
                if sid in connected_clients:
                    pending_count = len(connected_clients[sid]["pending_tool_calls"])
                    connected_clients[sid]["pending_tool_calls"] = {}
                    logger.info(f"🧹 Cleared {pending_count} pending tool calls for session {sid[:8]}...")
                
                # Notify the client
                emit('agent_stopped', {
                    'ok': True,
                    'message': 'Agent execution stop requested (deep agent + all subagents)',
                    'stopped': True
                })
                logger.info(f"📤 Sent 'agent_stopped' event to client")
            else:
                logger.warning(f"⚠️ No active agent execution found for user {user_id[:16]}...")
                emit('agent_stopped', {
                    'ok': False,
                    'message': 'No active agent execution to stop'
                })
        
        except Exception as e:
            logger.error(f"❌ Error stopping agent: {str(e)}")
            emit('agent_error', {'error': f'Error stopping agent: {str(e)}'})
