"""
DOM Analyzer Sub-Agent
Specialized agent for analyzing DOM structure and extracting relevant information
"""

from langchain.agents import create_agent
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from dotenv import load_dotenv
from typing import Optional
import os
import json
import logging

logger = logging.getLogger(__name__)

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

# Use a faster, cheaper model for DOM analysis
llm = ChatGroq(
    api_key=api_key,
    model="qwen/qwen3-32b",
    temperature=0.1,  # Low temperature for consistent analysis
)

# Global variable to store WebSocket callback (shared with main agent)
_websocket_callback = None

def set_websocket_callback(callback):
    """Set the callback function for WebSocket communication"""
    global _websocket_callback
    _websocket_callback = callback
    logger.info(f"✅ DOM Analyzer: WebSocket callback set")


# Tools specifically for DOM analysis
@tool
def analyze_page_structure(include_detailed_dom: bool = False) -> str:
    """
    Analyze the current page structure and return key information.
    
    Args:
        include_detailed_dom: Whether to include detailed DOM tree
        
    Returns:
        JSON string with page analysis including:
        - Page metadata (title, URL)
        - Interactive elements (buttons, links, forms)
        - Content structure (headings, sections)
        - Important attributes and identifiers
    
    Use this as the primary tool to understand what's on the page.
    """
    import asyncio
    try:
        result = asyncio.run(_websocket_callback("GET_PAGE_INFO", {
            "include_dom": include_detailed_dom,
            "extract_interactive": True,
            "extract_forms": True,
            "extract_media": True
        }))
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in analyze_page_structure: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})


@tool
def find_elements_by_criteria(selector: Optional[str] = None, text_content: Optional[str] = None, element_type: Optional[str] = None) -> str:
    """
    Find specific elements on the page based on criteria.
    
    Args:
        selector: CSS selector to find elements
        text_content: Text content to search for
        element_type: Type of element (button, link, input, etc.)
        
    Returns:
        JSON string with matching elements and their properties
    
    Use this to locate specific elements for interaction.
    """
    import asyncio
    try:
        params = {}
        if selector:
            params["selector"] = selector
        if text_content:
            params["text"] = text_content
        if element_type:
            params["element_type"] = element_type
            
        result = asyncio.run(_websocket_callback("FIND_ELEMENTS", params))
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in find_elements_by_criteria: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})


@tool
def extract_page_content(content_type: str = "all") -> str:
    """
    Extract specific content from the page.
    
    Args:
        content_type: Type of content to extract:
            - "all": All text content
            - "headings": Only headings (h1-h6)
            - "links": All links with URLs
            - "forms": Form structures
            - "tables": Table data
            
    Returns:
        JSON string with extracted content
    
    Use this to get structured content from the page.
    """
    import asyncio
    try:
        result = asyncio.run(_websocket_callback("EXTRACT_DOM", {
            "content_type": content_type
        }))
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in extract_page_content: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})


# Create the DOM analyzer sub-agent
dom_analyzer = create_agent(
    model=llm,
    tools=[analyze_page_structure, find_elements_by_criteria, extract_page_content],
    system_prompt="""You are a specialized DOM analysis agent. Your role is to analyze web pages and provide concise, actionable insights to the main agent.

RESPONSIBILITIES:
1. Analyze page structure and identify key elements
2. Find interactive elements (buttons, forms, links)
3. Extract relevant content and data
4. Provide clear, structured summaries

OUTPUT FORMAT:
Always return your analysis in a clear, structured format:

**Page Overview:**
- Title: [page title]
- URL: [current URL]
- Type: [e.g., form page, article, dashboard]

**Key Interactive Elements:**
- [List clickable elements with selectors]
- [List input fields with labels]
- [List buttons with text/purpose]

**Content Structure:**
- [Main headings and sections]
- [Important text or data]

**Recommendations:**
- [Suggested actions for the main agent]
- [Best selectors to use for interaction]

GUIDELINES:
- Be concise - focus on actionable information
- Prioritize interactive elements over static content
- Always include CSS selectors for elements
- Identify forms and their fields clearly
- Note any authentication requirements
- Highlight any errors or warnings on the page

Your goal is to give the main agent exactly what it needs to take action, without overwhelming it with unnecessary details."""
)

logger.info("✅ DOM Analyzer sub-agent created successfully")
