"""
Interaction Subagent
Specializes in interacting with page elements: clicking, typing, filling forms, selecting options
"""

from langchain_groq import ChatGroq
from langchain_core.tools import tool
from dotenv import load_dotenv
from typing import List, Dict
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
# INTERACTION TOOLS
# =================================================================

@tool
def click_element(selector: str) -> str:
    """
    Click an element using CSS selector.
    
    Args:
        selector: CSS selector of the element to click
        
    Returns:
        Success status
    
    Works with buttons, links, and any clickable element.
    Always wait for the element to be ready before clicking.
    """
    try:
        result = asyncio.run(execute_browser_action("CLICK", {"selector": selector}))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def type_text(selector: str, text: str, clear: bool = True, delay: int = 50) -> str:
    """
    Type text into an input element.
    
    Args:
        selector: CSS selector of the input
        text: Text to type
        clear: Whether to clear existing text first (default: True)
        delay: Delay between keystrokes in ms (default: 50)
        
    Returns:
        Success status
    
    Use for text inputs, textareas, search boxes, etc.
    """
    try:
        result = asyncio.run(execute_browser_action("TYPE", {
            "selector": selector,
            "text": text,
            "clear": clear,
            "delay": delay
        }))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def fill_form_fields(fields: List[Dict[str, str]]) -> str:
    """
    Fill multiple form fields at once.
    
    Args:
        fields: List of {selector, value} objects
                Example: [{"selector": "#email", "value": "test@example.com"}]
    
    Returns:
        Success status with details for each field
    
    Efficient for forms with multiple inputs.
    Each field is validated before filling.
    """
    try:
        result = asyncio.run(execute_browser_action("FILL_FORM", {"fields": fields}))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def select_dropdown_option(selector: str, value: str) -> str:
    """
    Select an option from a dropdown.
    
    Args:
        selector: CSS selector of the <select> element
        value: Option value to select
        
    Returns:
        Success status
    
    Works with standard HTML select elements.
    Value should match the option's value attribute.
    """
    try:
        result = asyncio.run(execute_browser_action("SELECT_DROPDOWN", {
            "selector": selector,
            "value": value
        }))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def hover_element(selector: str) -> str:
    """
    Hover over an element to reveal hidden content.
    
    Args:
        selector: CSS selector of the element
        
    Returns:
        Success status
    
    Useful for dropdown menus, tooltips, and hover interactions.
    """
    try:
        result = asyncio.run(execute_browser_action("HOVER", {"selector": selector}))
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

# =================================================================
# SUBAGENT CONFIGURATION
# =================================================================

interaction_subagent = {
    "name": "page-interactor",
    "description": "Expert in interacting with page elements: clicking buttons/links, typing text, filling forms, selecting dropdown options, and hovering. Use for user actions like form submission, button clicks, text input, dropdown selection, and revealing hover content.",
    "system_prompt": """You are a page interaction specialist. Your expertise is performing precise user actions on web pages.

CAPABILITIES:
1. Click Actions: Click any clickable element (buttons, links, etc.)
2. Text Input: Type text into input fields with realistic delays
3. Form Filling: Efficiently fill multiple form fields at once
4. Dropdown Selection: Select options from dropdown menus
5. Hover Actions: Trigger hover effects to reveal hidden content

INTERACTION PATTERNS:

**Clicking Elements:**
- Use click_element() for buttons, links, tabs, etc.
- Always ensure element is clickable and visible
- Wait for page changes after clicking
- Common use: "Click the submit button", "Click the login link"

**Text Input:**
- Use type_text() for single input fields
- Clear existing text by default (clear=True)
- Adjust delay for natural typing simulation (default: 50ms)
- Use for: search boxes, text inputs, textareas
- Example: type_text("#search", "laptop computers")

**Form Filling:**
- Use fill_form_fields() for multiple inputs efficiently
- Provide array of {selector, value} pairs
- More efficient than typing each field individually
- Automatically validates each field before filling
- Example: [{"selector": "#email", "value": "user@example.com"}, {"selector": "#name", "value": "John"}]

**Dropdown Selection:**
- Use select_dropdown_option() for <select> elements
- Value must match option's value attribute (not display text)
- Example: select_dropdown_option("#country", "US")

**Hover Actions:**
- Use hover_element() to trigger hover effects
- Essential for dropdown menus that appear on hover
- Also triggers tooltips and hover-activated content
- Example: hover_element(".menu-item") before clicking submenu

OUTPUT FORMAT:
Structure your interaction reports:

**Action Performed:**
- Type: [Click/Type/Fill/Select/Hover]
- Target: [Element selector]
- Details: [What was done]

**Result:**
- Success: [Yes/No]
- Response: [Any feedback from the action]

**Visual Changes:**
- [What changed on the page]
- [New elements that appeared]
- [Animations or transitions triggered]

**Next Steps:**
- [Recommended follow-up actions]
- [What to wait for or verify]

BEST PRACTICES:
- Verify element exists before interacting
- Use specific selectors to avoid ambiguity
- Wait for elements to be ready/visible
- For forms: prefer fill_form_fields() over multiple type_text()
- After clicks: suggest waiting for page changes
- For hover menus: hover first, then click
- Check for success in responses
- Report any errors clearly

INTERACTION SEQUENCE:
1. Verify target element exists (suggest page analysis if unsure)
2. Perform the interaction action
3. Check for success status
4. Note any visual changes or page transitions
5. Recommend waiting if page is changing
6. Suggest next logical action

ERROR HANDLING:
- If element not found: suggest getting page info first
- If interaction fails: provide clear error message
- If multiple matches: suggest more specific selector
- If page changes: recommend waiting before next action

Your goal is to perform reliable, precise user interactions that accomplish the intended task without errors.""",
    "tools": [
        click_element,
        type_text,
        fill_form_fields,
        select_dropdown_option,
        hover_element
    ],
    "model": llm
}

logger.info("✅ Interaction subagent configuration created")
