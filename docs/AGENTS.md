# AI Agents and Sub-Agents

The AI Browser Extension uses a multi-agent orchestrated system to distribute the workload autonomously.

## The Core 'Deep Agent'

The `deep_agent.py` acts as the primary orchestrator that leverages LangChain and a custom ReAct template loop (Reasoning & Acting) to understand a user's prompt. It is configured with access to a series of subagents (which act essentially as specialized tools).

When a user submits a natural language request, the **Deep Agent**:
1. Analyzes the objective.
2. Formulates a plan using ReAct.
3. Invokes the appropriate subagent to perform an action.
4. Returns a result to the user.

## Available Subagents

### 1. **Interaction Subagent (`interaction_subagent.py`)**
Responsible for acting on elements within the browser DOM. This agent handles filling forms, clicking buttons, submitting data, and typing text.

### 2. **Navigation Subagent (`navigation_subagent.py`)**
Specializes in moving the user across tabs (creating, closing, focusing) and manipulating URLs or history.

### 3. **Page Analysis & DOM Agent (`dom_analyzer_agent.py` / `page_analysis_subagent.py`)**
Instead of the backend downloading HTML from the user's browser, the frontend script semantically extracts only meaningful node structures (`semantic-dom-extractor.ts`).
This subagent takes that cleaned semantic schema and analyzes it to answer queries or assist the interaction subagent in finding elements.

### 4. **Timing Subagent (`timing_subagent.py`)**
Provides tools for scheduled interactions, waits, handling asynchronous loads, and timeouts when an element is dynamically mounted into the browser.

### 5. **Data Utility Subagent (`data_utility_subagent.py`)**
Responsible for internal data handling, formatting complex information returned by the LLM, preparing strings for the frontend UI, or summarizing large context blocks.

### 6. **Google Tools Subagent (`google_tools.py`)**
Handles searching the web via the Google Search API (or alternative SERP APIs) if the browser extension needs external facts to complete its task locally.

---

### Security and Boundaries
- Agents communicate state implicitly via a shared `conversation_manager.py`.
- No sensitive user session tokens are passed indiscriminately.
- Tools are sandboxed to only return specific string payloads to the agent.
- A **stop mechanism** exists in the side panel to interrupt the LangChain ReAct loop mid-execution via WebSocket.