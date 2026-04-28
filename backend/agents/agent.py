from langchain.agents import create_agent
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from langchain_core.tools import tool
from typing import Dict, Any, Optional, List, Union
import json
import os   
import asyncio
import logging

# Import Google tools
from .google_tools import google_tools, set_google_access_token

# Import DOM analyzer sub-agent
from .dom_analyzer_agent import dom_analyzer, set_websocket_callback as set_dom_analyzer_callback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGSMITH_PROJECT")

llm = ChatGroq(
    api_key=api_key,  # type: ignore
    model="openai/gpt-oss-120b",
    temperature=0.2,
)

# Global variable to store WebSocket communication callback
_websocket_callback = None

def set_websocket_callback(callback):
    """Set the callback function for WebSocket communication with the extension"""
    global _websocket_callback
    _websocket_callback = callback
    # Also set callback for DOM analyzer sub-agent
    set_dom_analyzer_callback(callback)
    logger.info(f"✅ WebSocket callback set successfully for main agent and DOM analyzer")

async def execute_browser_action(action_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a browser action via WebSocket and wait for response"""
    logger.info(f"\n{'='*60}")
    logger.info(f"🔨 EXECUTE_BROWSER_ACTION CALLED")
    logger.info(f"Action Type: {action_type}")
    logger.info(f"Params: {json.dumps(params, indent=2)}")
    logger.info(f"WebSocket callback set: {_websocket_callback is not None}")
    logger.info(f"{'='*60}\n")
    
    if _websocket_callback is None:
        logger.error("❌ WebSocket callback not set!")
        return {"success": False, "error": "WebSocket not connected"}
    
    try:
        logger.info(f"📞 Calling WebSocket callback...")
        result = await _websocket_callback(action_type, params)
        logger.info(f"✅ WebSocket callback returned")
        logger.info(f"Result: {json.dumps(result, indent=2) if isinstance(result, dict) else str(result)[:200]}")
        return result
    except Exception as e:
        logger.error(f"❌ Error in execute_browser_action: {str(e)}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        return {"success": False, "error": str(e)}

# =================================================================
# DOM ANALYZER SUB-AGENT TOOL
# =================================================================

@tool
def analyze_page_with_dom_expert(analysis_request: str) -> str:
    """
    Invoke the specialized DOM analyzer sub-agent to analyze the current page.
    
    Args:
        analysis_request: Describe what you need to know about the page.
                         Examples:
                         - "What interactive elements are on this page?"
                         - "Find all forms and their input fields"
                         - "Identify the main navigation structure"
                         - "Extract all clickable buttons and their purposes"
                         - "Analyze the page structure and suggest next actions"
    
    Returns:
        Detailed analysis from the DOM expert including:
        - Page overview and structure
        - Interactive elements with selectors
        - Content organization
        - Recommended actions
    
    Use this tool when you need expert analysis of the page structure before taking actions.
    The DOM analyzer specializes in understanding web pages and will provide targeted insights.
    """
    try:
        logger.info(f"🔍 Calling DOM analyzer sub-agent with request: {analysis_request[:100]}...")
        result = dom_analyzer.invoke({
            "messages": [{"role": "user", "content": analysis_request}]
        })
        
        # Extract the final message from the sub-agent
        messages = result.get('messages', [])
        if messages:
            final_response = messages[-1].content
            logger.info(f"✅ DOM analyzer returned analysis ({len(final_response)} chars)")
            return final_response
        else:
            return "DOM analyzer did not return any results."
    except Exception as e:
        logger.error(f"❌ Error calling DOM analyzer: {str(e)}")
        return f"Error analyzing page: {str(e)}"

# =================================================================
# SOPHISTICATED BROWSER AUTOMATION TOOLS
# =================================================================

@tool
def get_page_info(include_dom: bool = False) -> str:
    """
    Get comprehensive information about the current active page.
    
    Args:
        include_dom: If True, includes detailed DOM structure with interactive elements
        
    Returns:
        JSON string with page URL, title, interactive elements, forms, media, etc.
    
    Use this tool when you need to understand the current page structure before taking actions.
    """
    try:
        result = asyncio.run(execute_browser_action("GET_PAGE_INFO", {
            "include_dom": include_dom,
            "extract_interactive": True,
            "extract_forms": True,
            "extract_media": True
        }))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def extract_dom_structure(selector: Optional[str] = None, depth: int = 3) -> str:
    """
    Extract detailed DOM structure from the current page.
    
    Args:
        selector: CSS selector to extract specific part (None for entire page)
        depth: How deep to traverse the DOM tree (default: 3)
        
    Returns:
        JSON string with hierarchical DOM structure including all interactive elements
    
    Use this when you need to understand page layout, find specific elements, or analyze forms.
    """
    try:
        result = asyncio.run(execute_browser_action("EXTRACT_DOM", {
            "selector": selector,
            "depth": depth,
            "include_attributes": True,
            "include_text": True
        }))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def click_element(selector: str, wait_after: int = 500) -> str:
    """
    Click an element on the page using a CSS selector.
    
    Args:
        selector: CSS selector for the element to click (e.g., "#submit-btn", "button.primary")
        wait_after: Milliseconds to wait after clicking (default: 500)
        
    Returns:
        Success message or error details
    
    Use this for clicking buttons, links, checkboxes, or any clickable element.
    """
    try:
        result = asyncio.run(execute_browser_action("CLICK", {
            "selector": selector,
            "wait_after": wait_after
        }))
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def type_text(selector: str, text: str, clear_first: bool = True, press_enter: bool = False) -> str:
    """
    Type text into an input field or contenteditable element.
    
    Args:
        selector: CSS selector for the input element
        text: Text to type
        clear_first: Whether to clear existing text first (default: True)
        press_enter: Whether to press Enter after typing (default: False)
        
    Returns:
        Success message or error details
    
    Use this for filling forms, search boxes, chat inputs, or any text entry field.
    """
    try:
        result = asyncio.run(execute_browser_action("TYPE", {
            "selector": selector,
            "text": text,
            "clear_first": clear_first,
            "press_enter": press_enter
        }))
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def fill_form_fields(field_values: Dict[str, str], submit_selector: Optional[str] = None) -> str:
    """
    Fill multiple form fields at once and optionally submit.
    
    Args:
        field_values: Dictionary mapping CSS selectors to values
        submit_selector: Optional CSS selector for submit button
        
    Returns:
        Success message with details of filled fields
    
    Example:
        fill_form_fields({
            "input[name='email']": "user@example.com",
            "input[name='password']": "secret123",
            "select#country": "USA"
        }, "button[type='submit']")
    
    Use this for efficient form filling with multiple fields.
    """
    try:
        result = asyncio.run(execute_browser_action("FILL_FORM", {
            "fields": field_values,
            "submit_selector": submit_selector
        }))
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def select_dropdown_option(selector: str, value: Optional[str] = None, text: Optional[str] = None, index: Optional[int] = None) -> str:
    """
    Select an option from a dropdown menu.
    
    Args:
        selector: CSS selector for the select element
        value: Option value to select (preferred)
        text: Option text to select (alternative)
        index: Option index to select (0-based, fallback)
        
    Returns:
        Success message or error details
    
    Provide at least one of: value, text, or index.
    """
    try:
        result = asyncio.run(execute_browser_action("SELECT_DROPDOWN", {
            "selector": selector,
            "value": value,
            "text": text,
            "index": index
        }))
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def wait_for_element(selector: str, timeout: int = 10000, condition: str = "visible") -> str:
    """
    Wait for an element to meet a condition.
    
    Args:
        selector: CSS selector for the element
        timeout: Maximum wait time in milliseconds (default: 10000)
        condition: Condition to wait for - "visible", "hidden", "exists" (default: "visible")
        
    Returns:
        Success message when condition is met, or timeout error
    
    Use this when you need to wait for dynamic content to load or animations to complete.
    """
    try:
        result = asyncio.run(execute_browser_action("WAIT_FOR_ELEMENT", {
            "selector": selector,
            "timeout": timeout,
            "condition": condition
        }))
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def scroll_page(direction: str = "down", amount: int = 500, to_element: Optional[str] = None) -> str:
    """
    Scroll the page or scroll to a specific element.
    
    Args:
        direction: Scroll direction - "up", "down", "top", "bottom" (default: "down")
        amount: Pixels to scroll (used for up/down, default: 500)
        to_element: CSS selector to scroll to (overrides direction/amount)
        
    Returns:
        Success message with scroll position
    
    Use this to navigate long pages or bring specific elements into view.
    """
    try:
        result = asyncio.run(execute_browser_action("SCROLL", {
            "direction": direction,
            "amount": amount,
            "to_element": to_element
        }))
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def open_new_tab(url: str, activate: bool = True) -> str:
    """
    Open a new browser tab.
    
    Args:
        url: URL to open (use "about:blank" for empty tab)
        activate: Whether to switch to the new tab (default: True)
        
    Returns:
        New tab ID and success message
    
    Use this to navigate to new websites while keeping current page open.
    """
    try:
        result = asyncio.run(execute_browser_action("OPEN_TAB", {
            "url": url,
            "active": activate
        }))
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def close_current_tab() -> str:
    """
    Close the currently active tab.
    
    Returns:
        Success message or error details
    
    Use with caution - this will close the tab the agent is working on.
    """
    try:
        result = asyncio.run(execute_browser_action("CLOSE_TAB", {}))
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def switch_tab(tab_id: Optional[int] = None, direction: Optional[str] = None) -> str:
    """
    Switch to a different browser tab.
    
    Args:
        tab_id: Specific tab ID to switch to
        direction: Relative direction - "next" or "prev" (alternative to tab_id)
        
    Returns:
        Success message with new active tab info
    
    Provide either tab_id or direction.
    """
    try:
        result = asyncio.run(execute_browser_action("SWITCH_TAB", {
            "tab_id": tab_id,
            "direction": direction
        }))
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def navigate_to_url(url: str, wait_for_load: bool = True) -> str:
    """
    Navigate the current tab to a URL.
    
    Args:
        url: URL to navigate to
        wait_for_load: Whether to wait for page load complete (default: True)
        
    Returns:
        Success message when navigation completes
    
    Use this to change the current page URL.
    """
    try:
        result = asyncio.run(execute_browser_action("NAVIGATE", {
            "url": url,
            "wait_for_load": wait_for_load
        }))
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def get_all_tabs() -> str:
    """
    Get information about all open browser tabs.
    
    Returns:
        JSON array with tab info (id, url, title, active status)
    
    Use this to understand what tabs are open and select one to work with.
    """
    try:
        result = asyncio.run(execute_browser_action("GET_ALL_TABS", {}))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def take_screenshot(full_page: bool = False, selector: Optional[str] = None) -> str:
    """
    Take a screenshot of the current page.
    
    Args:
        full_page: Capture entire scrollable page (default: False for viewport only)
        selector: CSS selector to capture specific element only
        
    Returns:
        Base64 encoded image data or file path
    
    Use this to capture visual information from the page.
    """
    try:
        result = asyncio.run(execute_browser_action("SCREENSHOT", {
            "full_page": full_page,
            "selector": selector
        }))
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def get_element_text(selector: str, attribute: Optional[str] = None) -> str:
    """
    Extract text content or attribute value from an element.
    
    Args:
        selector: CSS selector for the element
        attribute: Optional attribute name to get (e.g., "href", "value", "data-id")
        
    Returns:
        Text content or attribute value
    
    Use this to read information from the page.
    """
    try:
        result = asyncio.run(execute_browser_action("GET_ELEMENT_TEXT", {
            "selector": selector,
            "attribute": attribute
        }))
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def get_element_attributes(selector: str) -> str:
    """
    Get all attributes of an element.
    
    Args:
        selector: CSS selector for the element
        
    Returns:
        JSON object with all element attributes
    
    Use this to inspect element properties like id, class, data attributes, etc.
    """
    try:
        result = asyncio.run(execute_browser_action("GET_ELEMENT_ATTRIBUTES", {
            "selector": selector
        }))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def execute_javascript(script: str, args: Optional[List[Any]] = None) -> str:
    """
    Execute custom JavaScript code in the page context.
    
    Args:
        script: JavaScript code to execute
        args: Optional arguments to pass to the script
        
    Returns:
        Result of the JavaScript execution
    
    Use this for custom automation that isn't covered by other tools.
    WARNING: Be careful with this tool - validate the script carefully.
    """
    try:
        result = asyncio.run(execute_browser_action("EXECUTE_SCRIPT", {
            "script": script,
            "args": args or []
        }))
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def get_cookies(url: Optional[str] = None) -> str:
    """
    Get essential authentication/session cookies for the current page.
    Returns only important cookies (session, auth, token, user) to avoid context overflow.
    
    Args:
        url: Optional URL to get cookies for (default: current page)
        
    Returns:
        JSON with filtered cookies (max 10), showing name, truncated value, and domain.
        Also includes total_cookies count and filtered flag.
    
    Use this to check authentication state. Look for cookies like:
    - session-id, session_token, sessionid
    - auth_token, auth, authentication
    - user_id, username, user
    - SSID, SID (Google)
    - c_user, xs (Facebook)
    
    Note: Returns minimal data to preserve context. Only essential auth cookies included.
    """
    try:
        result = asyncio.run(execute_browser_action("GET_COOKIES", {
            "url": url
        }))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def set_cookie(name: str, value: str, domain: Optional[str] = None, path: str = "/", 
               expires: Optional[int] = None) -> str:
    """
    Set a cookie for the current page.
    
    Args:
        name: Cookie name
        value: Cookie value
        domain: Cookie domain (default: current page domain)
        path: Cookie path (default: "/")
        expires: Expiration timestamp in seconds (default: session cookie)
        
    Returns:
        Success message or error details
    
    Use this to set authentication or preference data.
    """
    try:
        result = asyncio.run(execute_browser_action("SET_COOKIE", {
            "name": name,
            "value": value,
            "domain": domain,
            "path": path,
            "expires": expires
        }))
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def get_local_storage(key: Optional[str] = None) -> str:
    """
    Get data from localStorage.
    
    Args:
        key: Specific key to retrieve (None for all data)
        
    Returns:
        Value for specific key or all localStorage data
    
    Use this to access client-side stored data.
    """
    try:
        result = asyncio.run(execute_browser_action("GET_LOCAL_STORAGE", {
            "key": key
        }))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def set_local_storage(key: str, value: str) -> str:
    """
    Set data in localStorage.
    
    Args:
        key: Storage key
        value: Value to store (will be converted to string)
        
    Returns:
        Success message or error details
    
    Use this to persist data client-side.
    """
    try:
        result = asyncio.run(execute_browser_action("SET_LOCAL_STORAGE", {
            "key": key,
            "value": value
        }))
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def hover_element(selector: str, duration: int = 1000) -> str:
    """
    Hover over an element to trigger hover effects.
    
    Args:
        selector: CSS selector for the element
        duration: How long to hover in milliseconds (default: 1000)
        
    Returns:
        Success message or error details
    
    Use this to reveal dropdown menus or trigger hover-based UI changes.
    """
    try:
        result = asyncio.run(execute_browser_action("HOVER", {
            "selector": selector,
            "duration": duration
        }))
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def reload_page(bypass_cache: bool = False) -> str:
    """
    Reload the current page.
    
    Args:
        bypass_cache: If True, forces a hard reload (default: False)
        
    Returns:
        Success message when reload completes
    
    Use this to refresh the page content.
    """
    try:
        result = asyncio.run(execute_browser_action("RELOAD_TAB", {
            "bypass_cache": bypass_cache
        }))
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def go_back() -> str:
    """
    Navigate back to the previous page in history.
    
    Returns:
        Success message or error details
    
    Use this to undo navigation.
    """
    try:
        result = asyncio.run(execute_browser_action("GO_BACK", {}))
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def go_forward() -> str:
    """
    Navigate forward in browser history.
    
    Returns:
        Success message or error details
    
    Use this to redo navigation after going back.
    """
    try:
        result = asyncio.run(execute_browser_action("GO_FORWARD", {}))
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def find_elements(selector: str, filter_visible: bool = True) -> str:
    """
    Find all matching elements on the page.
    
    Args:
        selector: CSS selector to search for
        filter_visible: Only return visible elements (default: True)
        
    Returns:
        JSON array with information about matching elements
    
    Use this to discover multiple instances of elements.
    """
    try:
        result = asyncio.run(execute_browser_action("FIND_ELEMENTS", {
            "selector": selector,
            "filter_visible": filter_visible
        }))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

# Collect all tools
tools = [
    # DOM Analysis Sub-Agent (use this FIRST for complex page analysis)
    analyze_page_with_dom_expert,
    # Direct DOM Tools
    get_page_info,
    extract_dom_structure,
    click_element,
    type_text,
    fill_form_fields,
    select_dropdown_option,
    wait_for_element,
    scroll_page,
    open_new_tab,
    close_current_tab,
    switch_tab,
    navigate_to_url,
    get_all_tabs,
    take_screenshot,
    get_element_text,
    get_element_attributes,
    execute_javascript,
    get_local_storage,
    set_local_storage,
    hover_element,
    reload_page,
    go_back,
    go_forward,
    find_elements,
    # Google API tools
    *google_tools,
]

# Create agent using create_agent (LangChain 1.0+ format)
agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt="""You are a web automation AI agent with browser control tools and access to a specialized DOM analysis expert.

TOOLS AVAILABLE:
- DOM Expert: analyze_page_with_dom_expert (use this FIRST for complex page analysis)
- Page Analysis: get_page_info, extract_dom_structure, find_elements, get_element_text, take_screenshot
- Interactions: click_element, type_text, fill_form_fields, select_dropdown_option, hover_element
- Navigation: open_new_tab, switch_tab, navigate_to_url, go_back, reload_page, close_current_tab
- Data: get_local_storage, set_local_storage, execute_javascript
- Timing: wait_for_element, scroll_page
- Google: get_user_info, get_calendar_events, get_latest_emails, search_emails

WORKFLOW:
1. For complex pages/tasks: Call analyze_page_with_dom_expert() with a specific question
   - The DOM expert specializes in understanding page structure
   - It will provide actionable insights and recommended selectors
   - Use its recommendations for subsequent actions
2. For simple pages: Use get_page_info() directly
3. Plan step-by-step actions based on analysis
4. Execute one action at a time
5. Parse JSON results before proceeding
6. Use wait_for_element() after actions that change page

WHEN TO USE DOM EXPERT:
✓ First time visiting a complex website
✓ Need to find specific interactive elements
✓ Analyzing forms or multi-step workflows
✓ Unsure what actions are possible on the page
✗ Simple tasks like "go to URL" or "take screenshot"

BEST PRACTICES:
✓ Parse tool results: data = json.loads(result)
✓ Check success: if data.get("success")
✓ Wait after clicks: wait_for_element(selector, timeout=5000)
✓ Use specific selectors from get_page_info()
✓ Verify each step before proceeding
✗ Don't assume elements exist without checking
✗ Don't skip wait times after page changes
✗ Don't ignore tool errors

Execute methodically, validate each step, provide clear feedback."""
)


