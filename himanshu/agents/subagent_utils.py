"""
Shared utilities for all subagents
"""

import asyncio
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Global WebSocket callback shared across all subagents
_websocket_callback = None

def set_websocket_callback(callback):
    """Set the WebSocket callback for browser communication"""
    global _websocket_callback
    _websocket_callback = callback
    logger.info("✅ Shared WebSocket callback set for subagents")

async def execute_browser_action(action_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a browser action via WebSocket"""
    if _websocket_callback is None:
        logger.error("❌ WebSocket callback not set!")
        return {"success": False, "error": "WebSocket not connected"}
    
    try:
        result = await _websocket_callback(action_type, params)
        return result
    except Exception as e:
        logger.error(f"❌ Error in execute_browser_action: {str(e)}")
        return {"success": False, "error": str(e)}
