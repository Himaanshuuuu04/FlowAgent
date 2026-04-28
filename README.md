<h1 align="center">
  <br>AI Browser Extension</br>
</h1>

<p align="center">
  A sophisticated, AI-powered browser automation extension built for Chrome/Firefox, featuring a <b>React+WXT frontend</b> and a <b>Python/LangChain backend</b>.
</p>

## ✨ Project Overview

The **AI Browser Extension** enables autonomous web browsing and task automation via natural language commands. Using cutting-edge LLMs (such as Groq or Gemini), the system relies on a ReAct-based multi-agent architecture to analyze web pages, interact with DOM elements, manage tabs, and perform complex multi-step routines directly in your browser.

By removing heavy DOM parsing from the server and relying on a custom client-side semantic extractor, the extension is lightning fast, privacy-conscious, and highly accurate.

## 🚀 Quick Start

Ensure you have Python 3.11+ and Node.js 18+ installed.

### 1. Launch the Backend Using Docker (Recommended)
Make sure you have an `.env` file populated under `backend/.env` with your API keys.

```bash
docker-compose up -d --build
```
> Your backend will be accessible at `http://localhost:5000` via WebSockets. The FAISS database and SQLite files are automatically persisted in `./backend/data`.

### Alternative: Local Backend (Without Docker)
```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
pip install -r requirements.txt

# Run the context optimization setup script
# Windows
.\scripts\setup_context_optimization.bat
# Mac/Linux
bash ./scripts/setup_context_optimization.sh

python server.py
```
> Ensure your `.env` file is configured with your API keys (e.g. `GROQ_API_KEY`). By default, the WebSocket server runs on `http://localhost:5000`.

### 2. Launch the Frontend Extension
```bash
cd frontend
pnpm install
pnpm dev
```
> The WXT framework will automatically compile the extension and open a fresh Chromium profile with the extension loaded for debugging.

## 📚 Documentation

The extensive knowledge base and architectural guidelines for this project have been consolidated into the `docs/` folder for clarity:

- [System Architecture](docs/ARCHITECTURE.md) - Learn about the WebSocket flow, the Flask backend, and the React extension frontend.
- [Setup & Configuration](docs/SETUP.md) - Detailed instructions for installing dependencies, setting up the `.env` file, and running the RAG vector database.
- [AI Agents & Subagents](docs/AGENTS.md) - Overview of the LangChain ReAct loop, the Deep Agent, and the specialized subagents (Navigation, Interaction, DOM Analysis).

## 🛠️ Tech Stack

- **Frontend**: [WXT Framework](https://wxt.dev/), React, TypeScript, TailwindCSS
- **Backend**: Python, Flask, Flask-SocketIO
- **AI/Agents**: LangChain, Groq/Gemini, ChromaDB/FAISS (RAG)
- **Communication**: WebSockets (Real-time bidirectional)

## 🤝 Contributing

This project is structured as a monorepo for ease of development. The `frontend/` handles all Chrome Extension APIs and React UIs, while the `backend/` handles the LLM orchestration and vector database.

*Project restructured and documented for intern-level professional standards.*