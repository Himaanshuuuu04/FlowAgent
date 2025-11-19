"""
Unified Backend Server for AI Extension
Modularized architecture with separate concerns
"""
import os
import logging
from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import configuration
from config.settings import CLIENT_ID

# Import database
from conversation_db import get_conversation_db

# Import routes
from routes.api_routes import api_bp

# Import handlers
from handlers.websocket_handlers import register_handlers, init_handlers

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
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

# Get API key
api_key = os.getenv("GROQ_API_KEY")

# Get OAuth credentials
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")

# Initialize conversation database
conversation_db = get_conversation_db()

# Register API routes
app.register_blueprint(api_bp)

# Initialize and register WebSocket handlers
init_handlers(socketio, conversation_db)
register_handlers(socketio)

# =================================================================
# MAIN
# =================================================================

if __name__ == "__main__":
    logger.info("="*60)
    logger.info("🚀 Starting Unified Backend Server (Modularized)")
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
    logger.info("")
    logger.info("📂 Modular Architecture:")
    logger.info("   ├── config/settings.py - Configuration constants")
    logger.info("   ├── utils/token_utils.py - Token counting utilities")
    logger.info("   ├── routes/api_routes.py - HTTP/REST API endpoints")
    logger.info("   ├── handlers/websocket_handlers.py - WebSocket event handlers")
    logger.info("   ├── agents/ - AI agent implementations")
    logger.info("   └── conversation_db.py - Database layer")
    logger.info("="*60)
    
    # Run with SocketIO instead of Flask's run
    socketio.run(
        app,
        host="0.0.0.0",
        port=8080,
        debug=True,
        allow_unsafe_werkzeug=True
    )
