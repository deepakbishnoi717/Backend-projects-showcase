# 🧠 AI Knowledge Base — RAG + Chat API

> **Backend by Deepak Bishnoi · Frontend & UI developed by AI**

A production-ready AI Knowledge Base system built with **FastAPI**, **LangChain**, and **RAG (Retrieval Augmented Generation)**. Upload any document, ask questions, and get AI-powered answers — all through a sleek dark-themed web UI.

---

## ✨ Features

- 📤 **Document Upload** — Upload PDF, TXT, or DOCX files
- 🔍 **Semantic Search** — Search by meaning using vector embeddings (Sentence-BERT)
- 💬 **RAG Q&A** — Ask questions, get answers from your documents (zero hallucination)
- 🤖 **AI Chat** — Direct chat with LLaMA 3.3 70B, Gemma, Mixtral via Groq
- 🛠️ **AI Tools** — Text summarization and JSON extraction
- 🔐 **Security** — API key auth, rate limiting, request validation, guardrails
- 📊 **Audit Logging** — All requests logged to SQLite database
- 🌐 **Web UI** — Beautiful dark-themed single-page application

---

## 📁 Project Structure

```
ai-knowledge-base/
│
├── main.py                  # FastAPI app — routes, middleware, startup
├── backend.py               # AI chat engine (LangChain + Groq/OpenAI)
├── config.py                # App settings and constants
├── database.py              # SQLAlchemy models + audit log DB
├── schema.py                # Chat request/response Pydantic models
├── validators.py            # Input sanitization and validation
├── tool_schemas.py          # Summarize & JSON extraction schemas
│
├── kb_router.py             # Knowledge Base API routes (/kb/*)
├── kb_service.py            # RAG pipeline: load → chunk → embed → search → answer
├── kb_schemas.py            # KB Pydantic models (upload, search, Q&A)
├── kb_models.py             # DB models for document metadata
│
├── middleware/
│   ├── rate_limiter.py      # Per-IP rate limiting
│   ├── logging_middleware.py # Request/response logging
│   └── exception_handlers.py # Centralized error handling
│
├── static/
│   └── index.html           # Full web UI (dark theme, RAG chat, doc upload)
│
├── tests/
│   ├── test_kb.py           # Knowledge Base unit tests
│   └── test_tools.py        # AI Tools unit tests
│
├── uploads/                 # Runtime folder for uploaded documents
├── requirements.txt         # Python dependencies
├── pyproject.toml           # Project metadata
└── .python-version          # Python version pin (3.14.2)
```

---

## 🚀 Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/deepakbishnoi717/Backend-projects-showcase.git
cd Backend-projects-showcase
cd "project 2 - ai chatbot"
```

### 2. Create virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Mac/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables
Create a `.env` file in the root:
```env
GROQ_API_KEY=your_groq_api_key
OPENAI_API_KEY=your_openai_api_key       # optional
TAVILY_API_KEY=your_tavily_api_key       # optional (web search)
X_API_KEY=your_custom_api_key            # for /tools endpoints
```

### 5. Run the server
```bash
uvicorn main:app --reload
```

### 6. Open the UI
Visit **http://localhost:8000** — it auto-redirects to the dashboard.

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/chat` | Chat with AI model |
| `POST` | `/kb/upload` | Upload & process a document |
| `POST` | `/kb/search` | Semantic search across documents |
| `POST` | `/kb/answer` | RAG-powered Q&A from documents |
| `POST` | `/tools/summarize` | Summarize text (API key required) |
| `POST` | `/tools/extract_json` | Extract structured JSON from text |
| `GET` | `/ui` | Web UI dashboard |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI, Python 3.14 |
| **AI / LLM** | LangChain, LangGraph, Groq API |
| **Models** | LLaMA 3.3 70B, Gemma 2 9B, Mixtral 8x7B |
| **Embeddings** | Sentence-BERT (HuggingFace) |
| **Vector Store** | ChromaDB / FAISS |
| **Database** | SQLite (via SQLAlchemy) |
| **Frontend** | HTML, CSS, JavaScript (no framework) |
| **Security** | API key auth, rate limiting, input validation |

---

## 📸 UI Preview

| Page | Description |
|---|---|
| 🏠 Home | Dashboard with system stats |
| 📤 Upload | Drag & drop document upload |
| 💬 Chat | Ask AI or ask from your document |
| 🛠️ Tools | Summarize text, extract JSON |

---

## 👨‍💻 Credits

- **Backend Architecture & API Development** — [Deepak Bishnoi](https://github.com/deepakbishnoi717)
- **Frontend UI & Design** — AI-generated (Antigravity)

---

## 📄 License

MIT License — free to use, modify, and distribute.
