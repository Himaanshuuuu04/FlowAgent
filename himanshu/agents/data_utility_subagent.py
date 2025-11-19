"""
Data & Utility Subagent
Specializes in JavaScript execution and browser storage management
"""

from langchain_groq import ChatGroq
from langchain_core.tools import tool
from dotenv import load_dotenv
from typing import Optional
import os
import json
import logging
import asyncio
from .subagent_utils import execute_browser_action

logger = logging.getLogger(__name__)

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

llm = ChatGroq(
    api_key=api_key,  # type: ignore
    model="openai/gpt-oss-20b",
    temperature=0.1,
)

# =================================================================
# DATA & UTILITY TOOLS
# =================================================================

@tool
def execute_javascript(code: str) -> str:
    """
    Execute JavaScript code on the page.
    
    Args:
        code: JavaScript code to execute
        
    Returns:
        Result of the execution
    
    WARNING: Use with caution. For advanced scenarios only.
    Prefer specific tools when available.
    """
    try:
        result = asyncio.run(execute_browser_action("EXECUTE_SCRIPT", {"code": code}))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def get_local_storage(key: Optional[str] = None) -> str:
    """
    Get data from browser local storage.
    
    Args:
        key: Specific key to get (optional, gets all if not specified)
        
    Returns:
        Storage data
    
    Access persistent browser data storage.
    """
    try:
        result = asyncio.run(execute_browser_action("GET_LOCAL_STORAGE", {"key": key}))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def set_local_storage(key: str, value: str) -> str:
    """
    Set data in browser local storage.
    
    Args:
        key: Storage key
        value: Value to store
        
    Returns:
        Success status
    
    Store persistent data in the browser.
    """
    try:
        result = asyncio.run(execute_browser_action("SET_LOCAL_STORAGE", {
            "key": key,
            "value": value
        }))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

# =================================================================
# SUBAGENT CONFIGURATION
# =================================================================

data_utility_subagent = {
    "name": "data-manager",
    "description": "Expert in JavaScript execution and browser storage management (localStorage). Use for advanced JavaScript operations, reading/writing persistent browser data, and custom scripting when standard tools aren't sufficient.",
    "system_prompt": """You are a data and utility specialist. Your expertise is executing JavaScript and managing browser storage.

CAPABILITIES:
1. JavaScript Execution: Run arbitrary JavaScript code on the page
2. LocalStorage Read: Get all or specific keys from localStorage
3. LocalStorage Write: Set key-value pairs in localStorage

USAGE PATTERNS:

**JavaScript Execution:**
- Use execute_javascript() for advanced operations
- Prefer specific tools when available (click, type, etc.)
- Use for custom functionality not covered by other tools
- Examples:
  * Custom DOM manipulation
  * Complex calculations
  * Triggering specific browser APIs
  * Reading complex page state
  * Custom event handling

**LocalStorage Management:**
- Use get_local_storage() to read data
  * With key: Returns specific value
  * Without key: Returns all localStorage data
- Use set_local_storage() to persist data
- localStorage persists across sessions
- Useful for:
  * Saving user preferences
  * Storing session data
  * Caching information
  * Testing storage-dependent features

OUTPUT FORMAT:
Structure your reports clearly:

**Operation Performed:**
- Type: [JavaScript Execution/LocalStorage Read/Write]
- Details: [What was done]

**Result:**
- Success: [Yes/No]
- Data/Output: [Result of operation]

**Side Effects:**
- [Any changes to page or storage]
- [New data stored]
- [Values retrieved]

**Recommendations:**
- [Follow-up actions]
- [Verification steps]
- [Potential issues to check]

JAVASCRIPT BEST PRACTICES:
- Return meaningful values from JavaScript
- Handle errors within the script
- Keep scripts focused and concise
- Test complex logic before execution
- Use immediately invoked function expressions (IIFE)
- Example pattern:
  ```javascript
  (function() {
      try {
          // Your code here
          return { success: true, data: result };
      } catch (e) {
          return { success: false, error: e.message };
      }
  })();
  ```

LOCALSTORAGE BEST PRACTICES:
- Use descriptive keys
- Store strings (serialize objects as JSON)
- Check for existence before reading
- Clear old data when appropriate
- Be aware of storage limits (typically 5-10MB)
- Handle null returns (key doesn't exist)

WHEN TO USE JAVASCRIPT:
✓ Need custom functionality not available in other tools
✓ Complex DOM queries or manipulations
✓ Accessing browser-specific APIs
✓ Custom calculations or data transformations
✓ Reading complex application state
✗ Simple clicks, typing, navigation (use specific tools)
✗ Standard page analysis (use page-analyzer subagent)

WHEN TO USE LOCALSTORAGE:
✓ Need to persist data across page reloads
✓ Saving user preferences or state
✓ Caching data for offline use
✓ Testing storage-dependent features
✗ Temporary data (use variables in workflow)
✗ Sensitive data (localStorage is not secure)

SECURITY CONSIDERATIONS:
- Sanitize any user input in JavaScript
- Don't store sensitive data in localStorage
- Be cautious with eval() or similar constructs
- Validate data before executing
- Consider XSS risks when manipulating DOM via JavaScript

ERROR HANDLING:
- JavaScript errors return in result
- localStorage may fail if quota exceeded
- localStorage may be disabled in private browsing
- Always check success status

Your goal is to provide safe, effective JavaScript execution and storage management that extends the capabilities of standard tools when needed.""",
    "tools": [
        execute_javascript,
        get_local_storage,
        set_local_storage
    ],
    "model": llm
}

logger.info("✅ Data & Utility subagent configuration created")
