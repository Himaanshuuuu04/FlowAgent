# System Architecture Overview

## High-Level Architecture

The AI Browser Extension is a sophisticated browser automation system consisting of a Chrome/Firefox extension frontend and a powerful Python backend. It uses AI agents to understand natural language commands and execute complex browser automation tasks.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌────────────────────┐      ┌────────────────────┐                     │
│  │   Extension Popup  │      │   Side Panel       │                     │
│  │   - Quick Actions  │      │   - Agent UI       │                     │
│  │   - Tab Info       │      │   - Progress View  │                     │
│  │   - Settings       │      │   - Result Display │                     │
│  └────────────────────┘      └────────────────────┘                     │
└─────────────────────────────────────────────────────────────────────────┘
                                        ↕
                                  WebSocket (Real-time bidirectional)
                                        ↕
┌───────────────────────────────────────┴─────────────────────────────────┐
│                           PYTHON BACKEND                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌────────────────────┐      ┌────────────────────┐                     │
│  │  Flask Server      │      │  LangChain Agents  │                     │
│  │  - Socket.IO       │ ↔    │  - ReAct Reasoning │                     │
│  │  - Tool Handlers   │      │  - Groq LLMs       │                     │
│  └────────────────────┘      └────────────────────┘                     │
│             ↕                          ↕                                │
│  ┌────────────────────┐      ┌────────────────────┐                     │
│  │  Vector DB (FAISS/)│      │  Tools/Subagents   │                     │
│  │  - Context Storage │      │  - Navigation      │                     │
│  │  - RAG Retrieval   │      │  - Data Extraction │                     │
│  └────────────────────┘      └────────────────────┘                     │
└─────────────────────────────────────────────────────────────────────────┘
```

## Backend Modular Architecture (`backend/`)

The Python backend uses Flask + Socket.IO and LangChain, divided into clear modules for separation of concerns:

1.  **`server.py`**: The main entry point initializing the Flask app, database, and Socket.IO server.
2.  **`routes/api_routes.py`**: Handles REST API requests (e.g., fetching history, clearing history).
3.  **`handlers/websocket_handlers.py`**: Handles Socket.IO event registrations and dispatching requests from the frontend client.
4.  **`generator/conversation_manager.py`**: Orchestrates state management for conversations between the user and LLM.
5.  **`agents/deep_agent.py`** & **`agents/agent.py`**: The core AI reasoning logic (ReAct architecture using LangChain).
6.  **`agents/*_subagent.py`**: Specialized tools/agents handling specific tasks (Navigation, Interaction, Data Utility).
7.  **`utils/` / `config/`**: Shared settings, environment management, and token calculation utilities.

### Memory & State Management
- **SQLite Database (`conversation_manager.py`)**: Stores raw conversational history for users.
- **Vector Database (FAISS/Chroma)**: Used for RAG, embedding and saving DOM context or massive historic context securely without blowing up the primary context window.

## Frontend Extensions Architecture (`frontend/`)

Built with WXT (Web Extension Framework) alongside React + TypeScript.

1.  **Background Context (`background.ts`)**: 
    - Coordinates between the content scripts, popup, and side panel.
    - Connects to the backend via `websocket-client.ts`.
2.  **Content Script (`content.ts`)**:
    - Embedded in the user's active page.
    - Contains logic like semantic DOM extraction (`semantic-dom-extractor.ts`), parsing page content safely on the client side without needing the server to process heavy HTML parsing.
3.  **User Interface (`sidepanel/`, `popup/`)**:
    - React components (`AgentExecutor.tsx`, `ChatInterface.tsx` etc.)
    - Handles status visualization (WebSocket connections, Token usage).