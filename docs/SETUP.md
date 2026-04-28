# Getting Started & Setup

This guide will help you set up and run the AI Browser Extension locally.

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Google Chrome** or equivalent Chromium-based browser (Edge, Brave)
- An **API Key** for LLM services (e.g. Groq, Google Gemini API, OpenAI)

---

## 🏗️ 1. Backend Setup

The setup uses Python. We recommend creating an isolated environment like `venv` or `conda`.

### Install Dependencies

```bash
cd backend
python -m venv venv
# On Windows: venv\Scripts\activate
# On macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

### Environment Configuration

Create a `.env` file in the `backend/` directory:

```env
# Example .env Configuration
PORT=5000
HOST=0.0.0.0

# API Keys depending on the configured model
GROQ_API_KEY=your_groq_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
```

### Run the Server

Start the Flask + Socket.IO server:
```bash
python server.py
# The server will run on http://localhost:5000 by default.
```

---

## 🏗️ 2. Frontend Setup

The frontend uses the **WXT** framework for simplified web extension development with React and TypeScript.

### Install Dependencies

```bash
cd frontend
# We use pnpm based on the lockfile, but npm or yarn works too
pnpm install
```

### Run the Development Server

The WXT framework starts a dedicated browser instance for easy extension debugging:

```bash
pnpm dev
# or: npm run dev
```

> This command automatically builds the extension and launches a fresh Chromium profile with the dev extension loaded.

---

## 📦 3. Production Build

When ready to package for the Chrome Web Store:

```bash
cd frontend
pnpm build
```

This will output the compiled bundle to the `.output/` or `dist/` directory, which can be loaded into `chrome://extensions`.

---

## 🧠 4. RAG and Vector Environment

To enable RAG-based context retrieval for large conversations or page data, the backend initializes vector stores locally.

Ensure you have the embedding dependencies in `backend/requirements.txt`:
- `langchain-community`
- `langchain-chroma` (or `faiss-cpu`)
- `sentence-transformers`

The vector index directories (`faiss_db`, `chroma_db`) are created automatically inside the `backend/data/` folder upon first initialization.