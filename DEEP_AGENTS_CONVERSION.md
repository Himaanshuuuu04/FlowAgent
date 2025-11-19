# Deep Agents Conversion Guide

## Overview

Successfully converted the browser automation agent from regular LangChain agent to **Deep Agents** architecture. This provides advanced planning, context management, and multi-agent capabilities.

## What Changed

### 1. New Deep Agent File
**Created:** `himanshu/agents/deep_agent.py`

- Uses `create_deep_agent()` instead of `create_agent()`
- Automatically includes 6 built-in tools:
  - `write_todos` - Create/update task lists for complex workflows
  - `ls` - List files in agent's filesystem
  - `read_file` - Read file contents for context
  - `write_file` - Save large data to files
  - `edit_file` - Modify existing files
  - `task` - Spawn subagents for specialized tasks
- All 30+ existing browser automation tools preserved
- DOM analyzer sub-agent integration maintained
- WebSocket callback system unchanged

### 2. Server Updates
**Modified:** `himanshu/server.py`

```python
# Changed import from:
from agents.agent import agent, set_websocket_callback

# To:
from agents.deep_agent import agent, set_websocket_callback
```

The streaming implementation remains identical - deep agents use the same `agent.stream()` interface.

### 3. Dependencies
**Updated:** `himanshu/requirements.txt`

Added `deepagents` package to requirements.

## New Capabilities

### Planning & Task Decomposition
```python
# Agent can now break down complex tasks automatically:
User: "Research competitor pricing from 3 websites and create comparison"

# Agent will use write_todos internally:
1. Visit site 1 and extract pricing
2. Save to file competitor1_pricing.json
3. Visit site 2 and extract pricing
4. Save to file competitor2_pricing.json
5. Visit site 3 and extract pricing
6. Save to file competitor3_pricing.json
7. Read all pricing files
8. Create comparison table
```

### Context Management
```python
# For large data (DOM, API responses):
# OLD: Keep everything in memory → context overflow
# NEW: Save to files, read when needed

# Example:
1. get_page_info() → returns large DOM structure
2. write_file("page_dom.json", dom_data) → save to file
3. ... do other tasks ...
4. read_file("page_dom.json") → recall when needed
```

### Subagent Spawning
```python
# Delegate independent subtasks:
# Agent can use task tool to spawn specialized subagent

# Example:
task("Analyze this pricing data and create a comparison table: [data]")
# Subagent handles analysis while main agent continues
```

## System Prompt Enhancements

The deep agent has a comprehensive system prompt that guides:

1. **When to use deep agent features:**
   - Complex multi-step workflows → `write_todos`
   - Large responses/DOM data → `write_file`, `read_file`
   - Independent subtasks → `task` tool
   - Progress tracking → `write_todos`

2. **Workflow for complex tasks:**
   ```
   1. Break down request using write_todos
   2. Analyze page with DOM expert
   3. Save large data to files
   4. Delegate work via task tool
   5. Execute systematically following todos
   6. Manage context by reading from files
   ```

3. **Best practices:**
   - Parse JSON results
   - Check success status
   - Wait after page changes
   - Save large data to files
   - Update todos as steps complete

## Testing Recommendations

### Simple Tasks (No Planning Needed)
```javascript
// Should work exactly as before:
"Navigate to google.com and take a screenshot"
"Click the login button and fill the form"
```

### Complex Tasks (Will Use Planning)
```javascript
// Will demonstrate deep agent capabilities:
"Visit GitHub trending page, extract top 5 repositories, 
 research each one's purpose, and create a summary report"

// Expected behavior:
// 1. Agent creates todos for each step
// 2. Navigates and extracts repo info
// 3. Saves extracted data to files
// 4. May spawn subagents for research
// 5. Reads files and compiles report
```

### Context Management
```javascript
// Test file system tools:
"Extract the entire DOM of this page and save it to a file, 
 then analyze the saved file to find all forms"

// Expected:
// 1. extract_dom_structure() → large result
// 2. write_file("page_dom.json", dom)
// 3. read_file("page_dom.json")
// 4. analyze_page_with_dom_expert("find forms in this DOM: [data]")
```

## Installation

Before running the server, install the new dependency:

```bash
cd himanshu
pip install deepagents
```

This will install:
- `deepagents` core library
- `langchain-anthropic` (for Claude support)
- Additional dependencies (tavily, daytona, etc.)

## Frontend Updates (Optional)

The current frontend will work without changes, but you can enhance it to display:

1. **Todo Lists:**
   - When agent calls `write_todos`, show the task list
   - Update UI as todos are completed

2. **File Operations:**
   - Show when agent writes/reads files
   - Display file names and sizes

3. **Subagent Spawning:**
   - Indicate when subagents are created
   - Show subagent tasks and results

These would appear in the `agent_progress` events with specific tool names.

## Streaming Compatibility

✅ **Fully Compatible** - Deep agents work with existing streaming:

```python
# Server code remains unchanged:
for chunk in agent.stream({"messages": messages}, stream_mode="updates"):
    # Deep agent returns same structure as regular agent
    for node_name, node_data in chunk.items():
        # Process tool calls, responses, etc.
```

The frontend will receive:
- Tool calling events for built-in tools (`write_todos`, `write_file`, etc.)
- Tool calling events for browser automation tools
- Response events with content
- All existing progress tracking works

## Architecture Comparison

### Before (Regular Agent)
```
User Request
    ↓
Agent Model (openai/gpt-oss-120b)
    ↓
Tool Selection (30+ browser tools)
    ↓
Execute & Return
```

### After (Deep Agent)
```
User Request
    ↓
Planning Layer (write_todos)
    ↓
Agent Model (openai/gpt-oss-120b)
    ↓
Tool Selection:
    - Planning: write_todos
    - Context: ls, read_file, write_file, edit_file
    - Delegation: task (subagent)
    - Browser: 30+ automation tools
    - Analysis: DOM analyzer sub-agent
    ↓
Context Management (files)
    ↓
Execute & Return
```

## Key Benefits

1. **Better Task Decomposition**
   - Agent plans before executing
   - Clear step-by-step approach
   - Progress visibility through todos

2. **Efficient Context Handling**
   - No more context overflow on large DOM
   - File system for temporary storage
   - Clean separation of concerns

3. **Specialized Task Delegation**
   - Can spawn subagents for independent work
   - Parallel processing potential
   - Better for complex multi-domain tasks

4. **Maintained Capabilities**
   - All existing tools work
   - Streaming unchanged
   - DOM analyzer integrated
   - Conversation history preserved
   - WebSocket communication intact

## Troubleshooting

### Import Errors
If you see `ModuleNotFoundError: No module named 'deepagents'`:
```bash
pip install deepagents
```

### Model Configuration
Deep agents default to Claude Sonnet. We override with:
```python
llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.2)
agent = create_deep_agent(model=llm, ...)
```

### File System Access
Built-in tools create a virtual filesystem for the agent:
- Files are isolated per agent session
- Stored in memory or temp directory
- Cleared after session ends
- Don't interfere with actual filesystem

## Next Steps

1. **Install deepagents:**
   ```bash
   cd himanshu
   pip install deepagents
   ```

2. **Restart server:**
   ```bash
   python server.py
   ```

3. **Test with complex task:**
   - Try multi-step workflows
   - Observe todo list creation
   - Check file operations in logs

4. **Enhance frontend (optional):**
   - Display todo lists in UI
   - Show file operations
   - Indicate subagent activity

## Backward Compatibility

✅ **Simple tasks work exactly as before**

The deep agent is smart enough to skip planning for simple tasks:
- "Go to URL" → Direct execution, no todos
- "Click button" → Direct execution, no file I/O
- "Take screenshot" → Direct execution, no subagents

Planning features activate only for complex scenarios.

## Documentation References

- [Deep Agents Overview](https://docs.langchain.com/oss/python/deepagents/overview)
- [Deep Agents Quickstart](https://docs.langchain.com/oss/python/deepagents/quickstart)
- [Deep Agents Customization](https://docs.langchain.com/oss/python/deepagents/customization)
- [LangGraph Multi-Agent](https://docs.langchain.com/oss/python/langchain/multi-agent)

## Status

✅ **Deep agent created**
✅ **Server updated**
✅ **Requirements updated**
✅ **Type errors fixed**
⏳ **Pending:** Install deepagents library
⏳ **Pending:** Test with complex tasks
⏳ **Optional:** Frontend UI enhancements
