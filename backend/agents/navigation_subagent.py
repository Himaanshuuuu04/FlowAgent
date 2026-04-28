"""
Navigation Subagent
Specializes in browser navigation: opening tabs, switching between tabs, URL navigation, history control
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
# NAVIGATION TOOLS
# =================================================================

@tool
def navigate_to_url(url: str) -> str:
    """
    Navigate to a URL in the current tab.
    
    Args:
        url: Full URL to navigate to (must include http:// or https://)
        
    Returns:
        Success status with new page info
    
    Waits for the page to load before returning.
    Use get_page_info() after navigation to see what's on the new page.
    """
    try:
        result = asyncio.run(execute_browser_action("NAVIGATE", {"url": url}))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def open_new_tab(url: Optional[str] = None) -> str:
    """
    Open a new browser tab, optionally navigating to a URL.
    
    Args:
        url: URL to navigate to in new tab (optional)
        
    Returns:
        Success status with new tab ID
    
    The new tab becomes the active tab.
    """
    try:
        result = asyncio.run(execute_browser_action("OPEN_TAB", {"url": url}))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def close_current_tab() -> str:
    """
    Close the currently active tab.
    
    Returns:
        Success status
    
    Switches to another tab after closing.
    Cannot close if it's the last tab.
    """
    try:
        result = asyncio.run(execute_browser_action("CLOSE_TAB", {}))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def switch_tab(tab_id: int) -> str:
    """
    Switch to a specific browser tab.
    
    Args:
        tab_id: ID of the tab to switch to (get from get_all_tabs)
        
    Returns:
        Success status with new tab info
    
    Use get_all_tabs() first to see available tabs.
    """
    try:
        result = asyncio.run(execute_browser_action("SWITCH_TAB", {"tab_id": tab_id}))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def get_all_tabs() -> str:
    """
    Get information about all open browser tabs.
    
    Returns:
        List of tabs with id, title, url, and active status
    
    Use this to see all available tabs before switching.
    """
    try:
        result = asyncio.run(execute_browser_action("GET_ALL_TABS", {}))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def reload_page() -> str:
    """
    Reload the current page.
    
    Returns:
        Success status
    
    Waits for the page to reload before returning.
    """
    try:
        result = asyncio.run(execute_browser_action("RELOAD_TAB", {}))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def go_back() -> str:
    """
    Navigate back in browser history.
    
    Returns:
        Success status
    """
    try:
        result = asyncio.run(execute_browser_action("GO_BACK", {}))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def go_forward() -> str:
    """
    Navigate forward in browser history.
    
    Returns:
        Success status
    """
    try:
        result = asyncio.run(execute_browser_action("GO_FORWARD", {}))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

# =================================================================
# SUBAGENT CONFIGURATION
# =================================================================

navigation_subagent = {
    "name": "page-navigator",
    "description": "Expert in browser navigation: opening/closing tabs, switching between tabs, navigating to URLs, reloading pages, and using browser history (back/forward). Use for multi-tab workflows, URL navigation, page refreshing, and history navigation.",
    "system_prompt": """You are a browser navigation specialist. Your expertise is managing browser tabs and page navigation efficiently.

CAPABILITIES:
1. URL Navigation: Navigate to any URL in current or new tabs
2. Tab Management: Open, close, switch between tabs
3. Tab Discovery: List all open tabs with details
4. Page Refresh: Reload current page
5. History Navigation: Navigate back and forward in history

NAVIGATION PATTERNS:

**URL Navigation:**
- Use navigate_to_url() for same-tab navigation
- Always use full URLs with http:// or https://
- Waits for page load automatically
- Example: navigate_to_url("https://example.com")

**Multi-Tab Workflows:**
- Use open_new_tab() to open new tabs (with or without URL)
- New tab automatically becomes active
- Use get_all_tabs() to see all open tabs
- Use switch_tab(tab_id) to switch between tabs
- Use close_current_tab() when done with a tab
- Cannot close if it's the last tab

**Tab Information:**
- get_all_tabs() returns array with:
  * tab_id: Unique identifier for switching
  * title: Page title
  * url: Current URL
  * active: Boolean indicating active tab
- Use this before switching to find correct tab

**Page Refreshing:**
- Use reload_page() to refresh current page
- Useful after form submissions or data updates
- Waits for reload to complete

**History Navigation:**
- Use go_back() to navigate to previous page
- Use go_forward() to move forward in history
- Similar to browser back/forward buttons

OUTPUT FORMAT:
Structure your navigation reports:

**Navigation Action:**
- Type: [URL Navigation/Tab Operation/History Navigation/Page Reload]
- Details: [What was done]

**Current State:**
- Active Tab: [Tab ID and title]
- Current URL: [Where you are now]
- Total Tabs: [Number of open tabs]

**Result:**
- Success: [Yes/No]
- New Page Info: [If navigated to new page]

**Recommendations:**
- [Suggested next actions]
- [When to analyze new page]
- [Tab management suggestions]

BEST PRACTICES:
- Always use full URLs (include protocol)
- Get all tabs before switching
- Track active tab during multi-tab workflows
- Close tabs when done to avoid clutter
- Wait for page loads before analyzing
- Use new tabs for parallel tasks
- Reload page if data is stale
- Check success status after navigation

MULTI-TAB WORKFLOW EXAMPLE:
1. get_all_tabs() - See current state
2. open_new_tab("https://site1.com") - Open first site
3. [Work on site1]
4. open_new_tab("https://site2.com") - Open second site
5. [Work on site2]
6. get_all_tabs() - Find tab IDs
7. switch_tab(first_tab_id) - Go back to first site
8. close_current_tab() - Clean up when done

ERROR HANDLING:
- Invalid URL: Check protocol and format
- Tab not found: Use get_all_tabs() to verify ID
- Cannot close last tab: Switch before closing
- Navigation failed: Check URL validity

Your goal is to provide efficient, organized navigation that keeps workflow clear and manageable across multiple tabs and pages.""",
    "tools": [
        navigate_to_url,
        open_new_tab,
        close_current_tab,
        switch_tab,
        get_all_tabs,
        reload_page,
        go_back,
        go_forward
    ],
    "model": llm
}

logger.info("✅ Navigation subagent configuration created")
