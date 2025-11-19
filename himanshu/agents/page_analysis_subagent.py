"""
Page Analysis Subagent
Specializes in analyzing page structure, extracting DOM information, and finding elements
"""

from langchain_groq import ChatGroq
from langchain_core.tools import tool
from dotenv import load_dotenv
from typing import Optional, List
import os
import json
import logging
import asyncio
from .subagent_utils import execute_browser_action

logger = logging.getLogger(__name__)

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

# Use fast model for analysis tasks
llm = ChatGroq(
    api_key=api_key,  # type: ignore
    model="openai/gpt-oss-20b",
    temperature=0.1,
)

# =================================================================
# PAGE ANALYSIS TOOLS
# =================================================================

@tool
def get_page_info() -> str:
    """
    Get current page info with semantic DOM extraction.
    Returns ONLY actionable elements (buttons, links, inputs, forms) in viewport.
    
    This is optimized to return ~100-300 elements instead of 50k+ nodes.
    Each element includes: id, role, text, bounds, selector.
    
    Use this as your first step - it's token-efficient and gives you
    everything needed to interact with the page.
    """
    try:
        result = asyncio.run(execute_browser_action("GET_PAGE_INFO", {"viewport_only": True}))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def extract_dom_structure(selector: str = "body", max_depth: int = 3) -> str:
    """
    Extract detailed DOM structure from a specific element.
    
    Args:
        selector: CSS selector of root element (default: "body")
        max_depth: Maximum depth to traverse (default: 3, reduced to save tokens)
        
    Returns:
        Hierarchical structure with element types, classes, IDs, and text
    
    Use this when you need detailed information about page structure.
    Default depth is reduced to 3 to prevent context overflow.
    """
    try:
        result = asyncio.run(execute_browser_action("EXTRACT_DOM", {
            "selector": selector,
            "max_depth": max_depth
        }))
        return json.dumps(result, indent=2)
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

@tool
def get_element_text(selector: str) -> str:
    """
    Get the text content of an element.
    
    Args:
        selector: CSS selector of the element
        
    Returns:
        Text content of the element
    
    Extracts visible text from the element and its children.
    """
    try:
        result = asyncio.run(execute_browser_action("GET_ELEMENT_TEXT", {"selector": selector}))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def get_element_attributes(selector: str, attributes: Optional[List[str]] = None) -> str:
    """
    Get attributes of an element.
    
    Args:
        selector: CSS selector of the element
        attributes: List of attribute names to get (optional, gets all if not specified)
        
    Returns:
        Object with attribute name-value pairs
    
    Use to inspect element properties like href, src, class, id, etc.
    """
    try:
        result = asyncio.run(execute_browser_action("GET_ELEMENT_ATTRIBUTES", {
            "selector": selector,
            "attributes": attributes
        }))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def take_screenshot() -> str:
    """
    Capture a screenshot of the current page.
    
    Returns:
        Base64-encoded image data
    
    Useful for debugging or capturing page state.
    """
    try:
        result = asyncio.run(execute_browser_action("SCREENSHOT", {}))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def query_selector(selector: str) -> str:
    """
    Query specific elements by CSS selector.
    Returns semantic information about matching elements.
    
    Args:
        selector: CSS selector (e.g., "button.submit", "#search-input", "[data-testid='login']")
        
    Returns:
        List of matching elements with text, bounds, and selectors
    
    Use this when you need to find specific elements instead of getting
    the full page. Much more token-efficient for targeted queries.
    
    Examples:
        query_selector("button")  # All buttons
        query_selector(".search-box")  # Elements with search-box class
        query_selector("#main-content a")  # Links in main content
    """
    try:
        result = asyncio.run(execute_browser_action("QUERY_SELECTOR", {"selector": selector}))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def get_visible_elements() -> str:
    """
    Get ONLY elements currently visible in the viewport.
    
    Returns:
        Semantic elements in current viewport (typically 50-150 elements)
    
    Use this instead of get_page_info when you want to focus on
    what the user can currently see. Most token-efficient option.
    """
    try:
        result = asyncio.run(execute_browser_action("GET_VISIBLE_ELEMENTS", {}))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def get_text_content(selector: str) -> str:
    """
    Get just the text content of a specific element.
    
    Args:
        selector: CSS selector of the element
        
    Returns:
        Text content, innerText, and value (for inputs)
    
    Use this when you only need text, not full element info.
    Most token-efficient way to extract content.
    """
    try:
        result = asyncio.run(execute_browser_action("GET_TEXT_CONTENT", {"selector": selector}))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

# =================================================================
# SUBAGENT CONFIGURATION
# =================================================================

page_analysis_subagent = {
    "name": "page-analyzer",
    "description": "Expert in analyzing web pages using semantic DOM extraction. Provides query tools for token-efficient element discovery.",
    "system_prompt": """Page analysis specialist with semantic DOM extraction.

TOOLS (Token-Optimized):
1. get_visible_elements(): Viewport only (~50-150 elements, ~2K tokens) ⭐ START HERE
2. query_selector(selector): Query specific elements (~500-1K tokens)
3. get_text_content(selector): Extract text only (~200-500 tokens)
4. get_page_info(): Full semantic DOM (~100-300 elements, ~5K tokens)
5. Legacy tools: extract_dom_structure, find_elements (use sparingly)

WORKFLOW:
1. get_visible_elements() → See what's in viewport
2. query_selector("button") → Find specific elements
3. get_text_content("#main") → Extract content

Be concise. Focus on actionable elements.""",
    "tools": [
        get_visible_elements,
        query_selector,
        get_text_content,
        get_page_info,
        extract_dom_structure,
        find_elements,
        get_element_text,
        get_element_attributes,
        take_screenshot
    ],
    "model": llm
}

logger.info("✅ Page Analysis subagent configuration created")
