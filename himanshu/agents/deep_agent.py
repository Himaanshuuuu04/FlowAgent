"""
Deep Agent for browser automation with planning, context management, and specialized subagents.

Built using LangChain agents with TodoListMiddleware and custom subagent delegation.

Core Features:
- Planning: write_todos tool (via TodoListMiddleware) for task decomposition
- Context management: write_file, read_file, ls tools for handling large data
- Subagent delegation: task tool for delegating work to 5 specialized subagents
- Google API integration: Direct access to calendar, email, user info

Specialized Subagents (accessed via 'task' tool):
- page-analyzer: Page structure analysis, element discovery, content extraction (6 tools)
- page-interactor: User interactions, form filling, clicking, typing (5 tools)
- page-navigator: Browser navigation, tab management, history control (8 tools)
- data-manager: JavaScript execution, localStorage management (3 tools)
- page-synchronizer: Timing, waiting, scrolling for dynamic content (2 tools)

Total: 24 browser automation tools organized into specialized subagents + Google API tools
"""

from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_core.tools import tool
from typing import Dict, Any, List
import json
import os   
import logging

# Import Google tools
from .google_tools import google_tools, set_google_access_token

# Note: DOM analyzer agent removed - use page-analyzer subagent instead via task tool

# Import specialized subagents
from .page_analysis_subagent import page_analysis_subagent
from .interaction_subagent import interaction_subagent
from .navigation_subagent import navigation_subagent
from .data_utility_subagent import data_utility_subagent
from .timing_subagent import timing_subagent

# Import shared subagent utilities
from . import subagent_utils

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
langsmith_api_key = os.getenv("LANGSMITH_API_KEY")
langsmith_project = os.getenv("LANGSMITH_PROJECT")
if langsmith_api_key:
    os.environ["LANGSMITH_API_KEY"] = langsmith_api_key
if langsmith_project:
    os.environ["LANGSMITH_PROJECT"] = langsmith_project

# Use Groq's model for main agent
llm = ChatGroq(
    api_key=api_key,  # type: ignore
    model="openai/gpt-oss-120b",
    temperature=0.2,
)

def set_websocket_callback(callback):
    """Set the callback function for WebSocket communication with the extension"""
    # Set callback for all specialized subagents via shared utils
    subagent_utils.set_websocket_callback(callback)
    logger.info(f"✅ WebSocket callback set successfully for all specialized subagents")

# =================================================================
# SUBAGENT REGISTRY AND DELEGATION
# =================================================================

# Global registry of compiled subagents
_subagent_registry = {}
_filesystem = {}

def _compile_subagents(subagents: List[Dict[str, Any]]):
    """Compile subagent dictionaries into actual agents"""
    for subagent_config in subagents:
        name = subagent_config['name']
        model = subagent_config['model']
        tools = subagent_config['tools']
        system_prompt = subagent_config['system_prompt']
        
        # Create agent for this subagent
        subagent = create_agent(
            model=model,
            tools=tools,
            system_prompt=system_prompt
        )
        
        _subagent_registry[name] = {
            'agent': subagent,
            'description': subagent_config['description']
        }
        logger.info(f"✅ Compiled subagent: {name}")

@tool
def task(name: str, task_description: str) -> str:
    """
    YOUR PRIMARY TOOL - Delegate browser automation tasks to specialized subagents.
    
    USE THIS TOOL FOR ANY BROWSER ACTION - navigation, clicking, typing, analysis, etc.
    
    Args:
        name: Subagent name. MUST be one of:
              - "page-navigator": Navigate to URLs, open/close tabs, browser control
              - "page-analyzer": Get page structure, find elements, extract content
              - "page-interactor": Click elements, type text, fill forms
              - "data-manager": Execute JavaScript, manage localStorage
              - "page-synchronizer": Wait for elements, scroll, timing
        task_description: Detailed task description (be specific!)
        
    Returns:
        Result from the subagent execution
    
    EXAMPLES:
    - task(name="page-navigator", task_description="Navigate to https://youtube.com")
    - task(name="page-analyzer", task_description="Find all video links on the page")
    - task(name="page-interactor", task_description="Click the search button")
    
    This is your MAIN tool for browser control. Use it for ALL browser actions!
    """
    if name not in _subagent_registry:
        available = ', '.join(_subagent_registry.keys())
        return json.dumps({
            "success": False,
            "error": f"Unknown subagent '{name}'. Available: {available}"
        })
    
    try:
        logger.info(f"🔄 Delegating to subagent '{name}': {task_description[:100]}...")
        subagent_info = _subagent_registry[name]
        result = subagent_info['agent'].invoke({
            "messages": [{"role": "user", "content": task_description}]
        })
        
        # Extract the final response
        messages = result.get('messages', [])
        if messages:
            response = messages[-1].content
            logger.info(f"✅ Subagent '{name}' completed ({len(response)} chars)")
            return response
        else:
            return json.dumps({"success": False, "error": "No response from subagent"})
    except Exception as e:
        logger.error(f"❌ Error in subagent '{name}': {str(e)}")
        return json.dumps({"success": False, "error": str(e)})

@tool
def write_file(path: str, content: str) -> str:
    """
    Write content to a file (in-memory filesystem).
    
    Args:
        path: File path to write to
        content: Content to write
        
    Returns:
        Success status
    
    Use this to save large data (>1000 chars) to avoid context bloat.
    """
    global _filesystem
    _filesystem[path] = content
    return json.dumps({"success": True, "message": f"Wrote {len(content)} chars to {path}"})

@tool
def read_file(path: str) -> str:
    """
    Read content from a file (in-memory filesystem).
    
    Args:
        path: File path to read from
        
    Returns:
        File content
    
    Use this to retrieve previously saved data.
    """
    global _filesystem
    if path in _filesystem:
        return _filesystem[path]
    else:
        return json.dumps({"success": False, "error": f"File not found: {path}"})

@tool
def ls(path: str = "/") -> str:
    """
    List files in the filesystem.
    
    Args:
        path: Directory path (default: "/")
        
    Returns:
        List of files
    """
    global _filesystem
    files = list(_filesystem.keys())
    return json.dumps({"success": True, "files": files})

# =================================================================
# SYSTEM PROMPT FOR DEEP AGENT WITH SUBAGENTS
# =================================================================

DEEP_AGENT_SYSTEM_PROMPT = """You are an advanced web automation AI agent with FULL browser control through specialized subagents.

YOU HAVE THE 'task' TOOL - USE IT FOR ALL BROWSER ACTIONS!

AVAILABLE SUBAGENTS (access via task tool):
1. **page-navigator**: Navigate to URLs, open tabs, manage browser (USE THIS FIRST!)
   Example: task(name="page-navigator", task_description="Navigate to https://youtube.com")

2. **page-analyzer**: Analyze page structure, find elements, extract content
   Example: task(name="page-analyzer", task_description="Get all clickable elements on the page")

3. **page-interactor**: Click buttons, type text, fill forms, interact with elements
   Example: task(name="page-interactor", task_description="Click the search button and type 'music'")

4. **data-manager**: Execute JavaScript, manage localStorage
   Example: task(name="data-manager", task_description="Execute: document.querySelector('.play-btn').click()")

5. **page-synchronizer**: Wait for elements, scroll, handle dynamic content
   Example: task(name="page-synchronizer", task_description="Wait for video player to load")

YOUR DIRECT TOOLS:
- task(name, task_description): Delegate to subagents - THIS IS YOUR MAIN TOOL!
- write_todos: Break down complex tasks into steps
- write_file/read_file/ls: Store and retrieve information
- get_user_info/get_calendar_events/get_latest_emails/search_emails: Google API

CRITICAL RULES:
1. You HAVE the task tool - use it for ANY browser action!
2. NEVER say you can't control the browser - you can via task tool!
3. For navigation: task(name="page-navigator", task_description="Navigate to [URL]")
4. For interaction: task(name="page-interactor", task_description="Click [selector]")
5. For analysis: task(name="page-analyzer", task_description="Find [elements]")

CORRECT EXAMPLES:
✓ task(name="page-navigator", task_description="Open https://youtube.com in current tab")
✓ task(name="page-analyzer", task_description="Get all video titles and links from the page")
✓ task(name="page-interactor", task_description="Click the search box and type 'AI tutorials'")
✓ task(name="page-interactor", task_description="Click the first video in search results")

INCORRECT RESPONSES:
❌ "I don't have access to browser control" - YES YOU DO via task tool!
❌ "I can't navigate to websites" - YES YOU CAN via page-navigator subagent!
❌ "The task tool isn't available" - IT IS, use it!
❌ Explaining what the user should do - JUST USE THE TASK TOOL!

WORKFLOW FOR USER REQUESTS:
1. For complex tasks: Use write_todos to break into steps
2. For navigation: ALWAYS use task(name="page-navigator", task_description="Navigate to [URL]")
3. For page analysis: Use task(name="page-analyzer", task_description="Analyze page")
4. For interactions: Use task(name="page-interactor", task_description="Click/type action")
5. Present results clearly to user

REMEMBER: You have FULL browser control through the task tool. Use it immediately. Never say you can't!"""

# =================================================================
# AGENT CREATION WITH SUBAGENTS
# =================================================================

# Collect all specialized subagents
subagents = [
    page_analysis_subagent,
    interaction_subagent,
    navigation_subagent,
    data_utility_subagent,
    timing_subagent,
]

# Compile subagents into the registry
_compile_subagents(subagents)

# Collect direct tools (only tools that main agent uses directly)
direct_tools = [
    # Subagent delegation
    task,
    # Filesystem tools
    write_file,
    read_file,
    ls,
    # Google API tools
    *google_tools,
]

# Create deep agent with middleware
agent = create_agent(
    model=llm,
    tools=direct_tools,
    middleware=[
        TodoListMiddleware(
            system_prompt="Use the write_todos tool to break down complex tasks into manageable steps. Update the list as you progress."
        ),
    ],
    system_prompt=DEEP_AGENT_SYSTEM_PROMPT
)

logger.info(f"✅ Deep agent created with:")
logger.info(f"   - {len(direct_tools)} direct tools (task, filesystem, Google API)")
logger.info(f"   - {len(subagents)} specialized subagents:")
for subagent_config in subagents:
    logger.info(f"      * {subagent_config['name']}: {len(subagent_config['tools'])} tools")
logger.info(f"   - Middleware: TodoList (write_todos)")
logger.info(f"   - Total: 24 browser automation tools + {len(google_tools)} Google tools")
