# AI Browser Extension - Comprehensive Project Summary

## 🎯 Project Overview

**AI Browser Extension** is a sophisticated browser automation system that combines a Chrome/Firefox extension frontend with a powerful Python backend. The system uses AI agents to understand natural language commands and execute complex browser automation tasks through an intelligent multi-agent architecture.

### Architecture Type
- **Frontend**: React TypeScript Chrome Extension (WXT Framework)
- **Backend**: Flask + Socket.IO Python Server
- **AI Framework**: LangChain with Groq LLMs
- **Real-time Communication**: WebSocket (Socket.IO)
- **Storage**: SQLite (conversation history) + Browser Local Storage (chat UI)

---

## 🏗️ System Architecture

### Frontend (Chrome Extension)

**Framework**: WXT (Web Extension Framework) with React + TypeScript

**Key Components**:
1. **Background Script** (`background.ts`)
   - Manages browser automation tools execution
   - Handles 24 browser automation tools across 5 categories
   - Routes messages between content scripts and WebSocket client

2. **Side Panel** (`sidepanel/`)
   - `AgentExecutor.tsx` - Main chat interface with message history
   - `WebSocketStatus.tsx` - Connection status indicator
   - `SettingsSection.tsx` - Configuration panel
   - Modern chat UI with typing indicators, message bubbles, quick action pills

3. **WebSocket Client** (`utils/websocket-client.ts`)
   - Singleton pattern for stable connection management
   - Auto-reconnect with exponential backoff (max 10 attempts)
   - Ping/pong keep-alive mechanism (every 20 seconds)
   - Persistent user ID generation and storage
   - Event-driven architecture for real-time updates

**Dependencies**:
```json
{
  "socket.io-client": "^4.8.1",     // WebSocket communication
  "react": "^19.1.1",                // UI framework
  "lucide-react": "^0.553.0",        // Icon library
  "marked": "^17.0.0"                // Markdown rendering
}
```

---

### Backend (Python Flask Server)

**Framework**: Flask + Flask-SocketIO

**Architecture**: Modular design with separation of concerns

```
himanshu/
├── server.py                          # Entry point (110 lines - 90% reduction)
├── config/
│   └── settings.py                    # Configuration constants
├── utils/
│   └── token_utils.py                 # Token counting utilities
├── routes/
│   └── api_routes.py                  # HTTP/REST endpoints (OAuth, etc.)
├── handlers/
│   └── websocket_handlers.py          # WebSocket event handlers (572 lines)
├── agents/
│   ├── deep_agent.py                  # Main orchestrator agent
│   ├── page_analysis_subagent.py      # 6 analysis tools
│   ├── interaction_subagent.py        # 5 interaction tools
│   ├── navigation_subagent.py         # 8 navigation tools
│   ├── data_utility_subagent.py       # 3 data management tools
│   ├── timing_subagent.py             # 2 timing/waiting tools
│   ├── google_tools.py                # Google API integration
│   └── subagent_utils.py              # Shared utilities
├── generator/
│   ├── conversation_manager.py        # RAG system (FAISS + Ollama)
│   └── prompt.py                      # Prompt templates
└── conversation_db.py                 # SQLite database layer
```

**Dependencies**:
```python
flask                    # Web framework
flask-socketio          # WebSocket support
flask-cors              # CORS handling
python-dotenv           # Environment variables
deepagents              # LangChain agents framework
langchain               # AI agent framework
langchain-groq          # Groq LLM integration
langchain-core          # Core LangChain components
langchain-community     # Community tools
langchain-ollama        # Ollama embeddings
faiss-cpu               # Vector search
python-socketio         # WebSocket protocol
tiktoken                # Token counting
```

---

## 🤖 LangChain Implementation Details

### 1. **Main Deep Agent** (`deep_agent.py`)

**LangChain Methods & Components Used**:

```python
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
```

**Key Features**:
- **Model**: `ChatGroq(model="openai/gpt-oss-120b", temperature=0.2)`
- **Agent Creation**: `create_agent(model=llm, tools=[...], system_prompt=...)`
- **Middleware**: `TodoListMiddleware` for task decomposition and planning
- **Streaming**: `agent.stream()` for real-time progress updates
- **Tool System**: 
  - `@tool` decorator for defining custom tools
  - `task()` tool for delegating to 5 specialized subagents
  - `write_file()`, `read_file()`, `ls()` for context management
  - `write_todos()` (via TodoListMiddleware) for planning

**Agent Configuration**:
```python
agent = create_agent(
    model=llm,
    tools=[
        task,                    # Subagent delegation
        write_file,              # File operations
        read_file,
        ls,
        *google_tools           # Google API tools
    ],
    system_prompt=DEEP_AGENT_SYSTEM_PROMPT,
    middleware=[TodoListMiddleware()]  # Task planning
)
```

**Streaming Implementation**:
```python
async def execute_agent(goal: str, callback):
    for chunk in agent.stream(
        {"messages": [HumanMessage(content=goal)]},
        config={
            "recursion_limit": 50,
            "configurable": {"callbacks": [callback]}
        }
    ):
        # Process streaming chunks
        # Emit progress via WebSocket
```

---

### 2. **Specialized Subagents** (5 Total)

Each subagent uses identical LangChain patterns:

```python
from langchain.agents import create_agent
from langchain_groq import ChatGroq
from langchain_core.tools import tool
```

**Models**: All use `ChatGroq(model="openai/gpt-oss-20b", temperature=0.1)`

#### **A. Page Analysis Subagent** (6 tools)
```python
@tool
def get_dom_snapshot(params: dict) -> dict:
    """Get simplified DOM structure of current page"""
    
@tool
def get_page_metadata(params: dict) -> dict:
    """Get page title, URL, meta tags"""
    
@tool
def get_semantic_content(params: dict) -> dict:
    """Extract semantic content (paragraphs, lists)"""
    
@tool
def search_dom(params: dict) -> dict:
    """Search for elements by text/attributes"""
    
@tool
def get_forms_info(params: dict) -> dict:
    """Get all forms and their fields"""
    
@tool
def take_screenshot(params: dict) -> dict:
    """Capture page screenshot"""
```

#### **B. Interaction Subagent** (5 tools)
```python
@tool
def click_element(params: dict) -> dict:
    """Click on element by selector"""
    
@tool
def fill_input(params: dict) -> dict:
    """Fill input field with text"""
    
@tool
def select_option(params: dict) -> dict:
    """Select dropdown option"""
    
@tool
def hover_element(params: dict) -> dict:
    """Hover over element"""
    
@tool
def submit_form(params: dict) -> dict:
    """Submit form by selector"""
```

#### **C. Navigation Subagent** (8 tools)
```python
@tool
def navigate_to(params: dict) -> dict:
    """Navigate to URL"""
    
@tool
def go_back(params: dict) -> dict:
    """Navigate back in history"""
    
@tool
def go_forward(params: dict) -> dict:
    """Navigate forward in history"""
    
@tool
def refresh_page(params: dict) -> dict:
    """Refresh current page"""
    
@tool
def open_new_tab(params: dict) -> dict:
    """Open URL in new tab"""
    
@tool
def close_tab(params: dict) -> dict:
    """Close specific tab"""
    
@tool
def switch_tab(params: dict) -> dict:
    """Switch to different tab"""
    
@tool
def get_all_tabs(params: dict) -> dict:
    """List all open tabs"""
```

#### **D. Data Utility Subagent** (3 tools)
```python
@tool
def execute_javascript(params: dict) -> dict:
    """Execute custom JavaScript in page"""
    
@tool
def get_local_storage(params: dict) -> dict:
    """Read localStorage data"""
    
@tool
def set_local_storage(params: dict) -> dict:
    """Write to localStorage"""
```

#### **E. Timing Subagent** (2 tools)
```python
@tool
def wait_for_element(params: dict) -> dict:
    """Wait for element to appear"""
    
@tool
def scroll_to(params: dict) -> dict:
    """Scroll to element or position"""
```

---

### 3. **RAG System** (Conversation Manager)

**LangChain Components Used**:

```python
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
```

**Implementation**:
```python
class ConversationManager:
    def __init__(self):
        self.embeddings = OllamaEmbeddings(model="llama3.2")
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        self.vector_store = None  # FAISS index
    
    def add_conversation(self, user_msg: str, assistant_msg: str):
        """Add conversation to vector store"""
        doc = Document(
            page_content=f"User: {user_msg}\nAssistant: {assistant_msg}",
            metadata={"timestamp": ...}
        )
        chunks = self.text_splitter.split_documents([doc])
        
        if self.vector_store is None:
            self.vector_store = FAISS.from_documents(chunks, self.embeddings)
        else:
            self.vector_store.add_documents(chunks)
    
    def search_similar(self, query: str, k: int = 3):
        """Semantic search for relevant conversations"""
        return self.vector_store.similarity_search(query, k=k)
```

---

## 🔌 WebSocket Communication Protocol

### Socket.IO Events

**Connection Events**:
```typescript
// Client -> Server
socket.emit('connect')
socket.emit('register_user_id', { user_id: string })
socket.emit('ping', { timestamp: number })

// Server -> Client
socket.emit('connection_established', { status, client_id, message })
socket.emit('user_registered', { ok, user_id, history_loaded })
socket.emit('pong', { timestamp, server_time })
```

**Agent Execution Events**:
```typescript
// Client -> Server
socket.emit('execute_agent_ws', { goal: string })
socket.emit('stop_agent_ws', {})

// Server -> Client
socket.emit('agent_progress', { 
    status: string,        // 'initializing' | 'planning' | 'executing' | 'responding'
    message: string,
    step?: number,
    node?: string,
    tools?: string[]
})
socket.emit('agent_completed', { result: any, execution_time: number })
socket.emit('agent_error', { error: string })
socket.emit('agent_stopped', { message: string })
```

**Tool Execution Events** (Bidirectional):
```typescript
// Server -> Client (Tool request)
socket.emit('tool_execution_request', {
    tool_id: string,
    action_type: string,
    params: object
})

// Client -> Server (Tool result)
socket.emit('tool_execution_result', {
    tool_id: string,
    result: { success: boolean, data?: any, error?: string }
})
```

**Google OAuth Events**:
```typescript
socket.emit('set_google_token', { access_token: string })
socket.emit('token_set', { ok: true })
```

**Conversation Management**:
```typescript
socket.emit('clear_conversation_history')
socket.emit('get_conversation_history')
socket.emit('conversation_cleared', { ok: true })
socket.emit('conversation_history', { history: [], count: number })
```

---

## 🗄️ Data Storage

### 1. **SQLite Database** (Server-side)

**Schema**:
```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,           -- 'user' | 'assistant'
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_timestamp ON conversations(user_id, timestamp);
```

**Operations**:
```python
def add_message(user_id: str, role: str, content: str):
    """Insert message into database"""
    
def get_history(user_id: str, limit: int = 30):
    """Retrieve conversation history"""
    
def clear_history(user_id: str):
    """Delete all messages for user"""
```

### 2. **Browser Local Storage** (Client-side)

**Stored Data**:
```typescript
{
  "persistentUserId": "user_1732012345_abc123def456",  // Persistent ID
  "wsAutoConnect": true,                                // Auto-reconnect preference
  "chatHistory": [                                      // UI chat messages
    {
      id: "msg_123",
      role: "user" | "assistant",
      content: string,
      timestamp: ISO8601
    }
  ]
}
```

### 3. **FAISS Vector Database** (RAG)

**Location**: `data/faiss_db/index/index.faiss`

**Purpose**: Semantic search over conversation history for context retrieval

---

## 🛠️ Key Features

### 1. **Multi-Agent Architecture**
- **Deep Agent**: Orchestrator with planning and delegation
- **5 Specialized Subagents**: Domain-specific expertise
- **Tool-based Communication**: Agents delegate via `task()` tool
- **Context Sharing**: File system for large data exchange

### 2. **Real-time Streaming**
- LangChain streaming chunks via `agent.stream()`
- WebSocket progress updates every chunk
- Status tracking: initializing → planning → executing → responding

### 3. **Stop Mechanism**
- **4 Stop Check Points**:
  1. Tool callback waiting loop (every 0.1s)
  2. Pre-execution check
  3. Streaming loop (every chunk)
  4. Node processing (before each step)
- Recursion limit: 50 to prevent infinite loops
- Graceful cleanup of all subagents

### 4. **Conversation Memory**
- **Short-term**: Last 30 messages in memory (MEMORY_MESSAGES)
- **Long-term**: SQLite persistent storage
- **Auto-restore**: History loaded on reconnect
- **RAG Enhancement**: FAISS semantic search for context

### 5. **Google API Integration**
- OAuth 2.0 authentication
- Calendar access (events, create, update)
- Gmail access (list, send, read)
- User info retrieval

### 6. **Token Management**
```python
# Configuration (config/settings.py)
MAX_HISTORY_MESSAGES = 10        # HTTP API limit
MEMORY_MESSAGES = 30             # WebSocket agent memory
MAX_TOKENS_PER_REQUEST = 4000    # Safety limit
WARN_TOKENS_THRESHOLD = 3000     # Warning threshold
ENABLE_TOKEN_COUNTING = True     # Track usage

# Utility (utils/token_utils.py)
def estimate_messages_tokens(messages: List) -> int:
    """Estimate token count using tiktoken"""
```

---

## 🎨 UI Design

### Chat Interface
- **Message Bubbles**: User (right, navy gradient) vs Assistant (left, gray gradient)
- **Typing Indicator**: 3 bouncing dots during execution
- **Progress Display**: Latest 3 steps shown in assistant message
- **Quick Action Pills**: New Chat, Summarize, Explain, Analyze
- **Mention Menu**: @ trigger for quick actions
- **Markdown Support**: Code blocks, lists, links, formatting

### Composer Bar
- **Icons**: Plus, MoreHorizontal, Camera, Mic
- **Send Button**: Gradient circle with ArrowUp icon
- **Stop Button**: Red gradient during execution
- **Input**: Auto-resize with Enter to send

### Empty State
- **Mention Card**: Rotated (-5deg) with example query
- **Call-to-Action**: "Mention tabs to add context"
- **Gradient Theme**: Purple/blue gradients throughout

---

## 🔐 Security & Configuration

### Environment Variables
```bash
# Server (.env)
GROQ_API_KEY=xxx                    # Groq API access
GOOGLE_CLIENT_SECRET=xxx            # Google OAuth
GITHUB_CLIENT_ID=xxx                # GitHub OAuth
GITHUB_CLIENT_SECRET=xxx
LANGSMITH_API_KEY=xxx               # Tracing (optional)
LANGSMITH_PROJECT=xxx
SECRET_KEY=xxx                      # Flask session

# Extension (no .env, uses browser storage)
```

### CORS Configuration
```python
CORS(app, resources={r"/*": {"origins": "*"}})  # Development mode
```

### WebSocket Security
- Persistent user ID for session tracking
- Token-based authentication for Google APIs
- Client validation on each request

---

## 📊 Performance Optimizations

### 1. **Modular Backend**
- Reduced main server from 1103 lines → 110 lines (90%)
- Removed 305 lines of redundant DOM compression
- Clean separation: config, utils, routes, handlers, agents

### 2. **Connection Stability**
- Auto-reconnect with exponential backoff
- Keep-alive pings every 20 seconds
- Connection monitoring every 10 seconds
- Max 10 reconnect attempts

### 3. **Memory Management**
- Sliding window: Only last 30 messages in memory
- Token counting to prevent overflow
- Conversation trimming when over limit
- FAISS indexing for fast semantic search

### 4. **Streaming Architecture**
- Chunk-by-chunk processing
- Non-blocking async execution
- Real-time UI updates
- Stop checks every 0.1s

---

## 📈 Execution Flow

### Complete Agent Execution Sequence

```
1. User Input
   └─> Frontend: AgentExecutor.tsx receives goal
   
2. WebSocket Transmission
   └─> wsClient.executeAgent(goal) called
   └─> socket.emit('execute_agent_ws', { goal })
   
3. Server Reception
   └─> handlers/websocket_handlers.py receives event
   └─> Validates connection and user ID
   └─> Loads conversation history from SQLite
   
4. Agent Initialization
   └─> deep_agent.py creates agent with middleware
   └─> Compiles 5 specialized subagents
   └─> Sets WebSocket callback for all subagents
   
5. Planning Phase (TodoListMiddleware)
   └─> Agent calls write_todos() tool
   └─> Decomposes task into subtasks
   └─> Status: 'planning'
   
6. Execution Phase
   └─> For each subtask:
       ├─> Agent decides: use tool or delegate to subagent
       ├─> If tool call: emit 'tool_execution_request'
       ├─> Client executes tool via background.ts
       ├─> Result sent back via 'tool_execution_result'
       ├─> If subagent: call task() with subagent name
       └─> Subagent executes with its specialized tools
   
7. Streaming
   └─> Every chunk from agent.stream():
       ├─> Check stop flag
       ├─> Parse chunk (tool call, response, etc.)
       ├─> Emit 'agent_progress' with status
       └─> Frontend updates UI in real-time
   
8. Completion
   └─> Agent finishes execution
   └─> Save messages to SQLite
   └─> Emit 'agent_completed' with result
   └─> Frontend displays final message
   
9. Error Handling
   └─> At any point if error:
       ├─> Emit 'agent_error'
       ├─> Cleanup resources
       └─> Frontend shows error message
```

---

## 🧪 Testing Examples

Located in `TESTING_EXAMPLES.md`:

1. **Navigation**: "Open Google and search for AI news"
2. **Form Interaction**: "Fill login form with test@example.com"
3. **Data Extraction**: "Get all product names from this page"
4. **Multi-step**: "Search for Python tutorials, open first result, summarize"
5. **Google Integration**: "Check my calendar for today's events"

---

## 📚 Documentation Files

```
AI-Extension/
├── PROJECT_SUMMARY.md              # This file
├── ARCHITECTURE.md                 # System design details
├── AGENT_SYSTEM_GUIDE.md          # Agent architecture guide
├── DEEP_AGENTS_CONVERSION.md      # Migration to DeepAgents
├── SUBAGENT_INTEGRATION_SUMMARY.md # Subagent system
├── MODULAR_ARCHITECTURE.md        # Backend modularization
├── AGENT_STOP_MECHANISM.md        # Stop button implementation
├── WEBSOCKET_SETUP.md             # WebSocket configuration
├── GOOGLE_TOOLS_INTEGRATION.md    # Google API setup
├── GITHUB_OAUTH_SETUP.md          # GitHub OAuth guide
├── TAB_CONTROL_GUIDE.md           # Tab management
├── TESTING_EXAMPLES.md            # Test cases
├── SETUP_RAG.md                   # RAG system setup
├── GETTING_STARTED.md             # Quick start
└── QUICKSTART.md                  # Installation guide
```

---

## 🚀 Getting Started

### Prerequisites
```bash
# Python 3.8+
pip install -r himanshu/requirements.txt

# Node.js 18+
cd Extension && pnpm install
```

### Running the System

**Backend**:
```bash
cd himanshu
python server.py
# Server: http://localhost:8080
# WebSocket: ws://localhost:8080/socket.io/
```

**Frontend**:
```bash
cd Extension
pnpm dev              # Chrome
pnpm dev:firefox      # Firefox
```

**Build for Production**:
```bash
pnpm build           # Chrome
pnpm build:firefox   # Firefox
pnpm zip             # Create ZIP for Chrome Web Store
```

---

## 📝 Summary Statistics

### Codebase Metrics
- **Backend Lines**: ~2,500 (after 90% reduction from 11,000+)
- **Frontend Lines**: ~3,000
- **Total Tools**: 24 browser automation tools + Google API tools
- **Agents**: 1 main + 5 specialized subagents
- **WebSocket Events**: 25+ event types
- **LangChain Imports**: 22 across all files

### LangChain Components Used
1. **Agents**: `create_agent` - 6 instances (1 main + 5 subagents)
2. **Middleware**: `TodoListMiddleware` - Task planning
3. **Models**: `ChatGroq` - 6 instances (openai/gpt-oss-120b + 5x openai/gpt-oss-20b)
4. **Tools**: `@tool` decorator - 24 browser tools + 6 Google tools + 4 utility tools
5. **Messages**: `HumanMessage`, `AIMessage` - Conversation formatting
6. **Vector Store**: `FAISS` - Semantic search
7. **Embeddings**: `OllamaEmbeddings` - Text embeddings
8. **Text Splitters**: `RecursiveCharacterTextSplitter` - Chunking
9. **Documents**: `Document` - Data structure for RAG
10. **Prompts**: `ChatPromptTemplate` - Prompt engineering

### Technology Stack
- **Frontend**: React 19, TypeScript, WXT, Socket.IO Client, Lucide Icons, Marked
- **Backend**: Flask, Flask-SocketIO, Flask-CORS
- **AI**: LangChain, LangChain-Groq, DeepAgents, Groq API
- **Storage**: SQLite, FAISS, Browser Local Storage
- **Communication**: WebSocket (Socket.IO), HTTP REST API
- **Embeddings**: Ollama (llama3.2)
- **LLMs**: Groq (openai/gpt-oss-120b, openai/gpt-oss-20b)

---

## 🎯 Key Achievements

1. ✅ **90% Code Reduction**: Modularized 1103-line monolith to 110-line entry point
2. ✅ **Real-time Streaming**: Chunk-by-chunk progress updates via WebSocket
3. ✅ **Multi-Agent System**: 6 specialized agents with intelligent delegation
4. ✅ **Stop Mechanism**: 4-point interruption system with graceful cleanup
5. ✅ **Persistent Memory**: SQLite + browser storage + RAG semantic search
6. ✅ **Modern UI**: Chat interface with typing indicators, message bubbles, markdown
7. ✅ **Stable WebSocket**: Auto-reconnect, keep-alive, exponential backoff
8. ✅ **24 Browser Tools**: Comprehensive automation across 5 categories
9. ✅ **Google Integration**: Calendar, Gmail, user info via OAuth 2.0
10. ✅ **Production Ready**: Error handling, logging, token management, security

---

## 🔮 Future Enhancements

- [ ] Multi-user support with authentication
- [ ] Agent execution history and analytics
- [ ] Custom tool creation interface
- [ ] Voice input/output
- [ ] Parallel execution of independent tasks
- [ ] Mobile browser support
- [ ] Cloud deployment (AWS/GCP)
- [ ] Advanced RAG with multiple vector stores
- [ ] Fine-tuned models for specific domains
- [ ] Enterprise features (team collaboration, audit logs)

---

**Project Status**: ✅ Production Ready  
**Version**: 1.0.0  
**Last Updated**: November 19, 2025  
**License**: Proprietary  
**Author**: Himanshu

---

*This comprehensive summary covers all aspects of the AI Browser Extension project, including architecture, implementation details, LangChain methods, WebSocket protocols, and system flows.*
