# 🧠 ResearchGPT

**AI-powered research paper assistant** — upload PDFs, index them into a vector database, and ask citation-backed questions powered by Google Gemini.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

---

## ✨ Features

- 🔐 **Secure Authentication** — User registration and login with hashed passwords
- 📄 **PDF Upload & Parsing** — Upload research papers with automatic chunking and embedding
- 🤖 **RAG Chat** — Ask questions and get citation-backed answers with page numbers
- 📝 **Paper Summarization** — Generate structured executive summaries of uploaded papers
- 🔍 **Semantic Search** — Find relevant passages across all uploaded papers
- 👤 **Per-User Isolation** — Each user has their own paper library and vector space
- 📊 **Document Status Tracking** — Real-time status: `uploaded` → `processing` → `ready` / `failed`
- ☁️ **Cloud-Ready Architecture** — Swap local backends for S3, Pinecone, PostgreSQL, and Redis
- 🐳 **Docker & Gunicorn** — Production-ready containerized deployment
- 🩺 **Health Check Endpoint** — `/health` route for cloud platform probes

---

## 🏗️ Architecture

```mermaid
graph TB
    subgraph Client
        Browser["Browser (Flask Templates)"]
    end

    subgraph Application
        Flask["Flask Web App"]
        Gunicorn["Gunicorn WSGI Server"]
        Worker["RQ Worker (optional)"]
    end

    subgraph Data Layer
        DB["PostgreSQL / SQLite"]
        Storage["Local Disk / AWS S3"]
        VectorDB["ChromaDB / Pinecone"]
        Redis["Redis Queue (optional)"]
    end

    subgraph External APIs
        Gemini["Google Gemini API"]
        HF["HuggingFace Embeddings"]
    end

    Browser --> Gunicorn --> Flask
    Flask --> DB
    Flask --> Storage
    Flask --> VectorDB
    Flask --> Redis
    Redis --> Worker
    Worker --> VectorDB
    Worker --> DB
    Flask --> Gemini
    Flask --> HF
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask, Flask-Login, Flask-SQLAlchemy |
| AI / ML | LangChain, Google Gemini, HuggingFace sentence-transformers |
| Vector Store | ChromaDB (local) or Pinecone (cloud) |
| Database | SQLite (dev) or PostgreSQL (production) |
| File Storage | Local disk (dev) or AWS S3 (production) |
| Task Queue | Synchronous (dev) or Redis + RQ (production) |
| Deployment | Docker, Gunicorn, Render |

---

## 🚀 Quick Start (Local Development)

### 1. Clone and setup

```bash
git clone https://github.com/YOUR_USERNAME/ResearchGPT.git
cd ResearchGPT
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

### 2. Configure environment

```bash
copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux
```

Edit `.env` and add your Gemini API key:

```env
GEMINI_API_KEY=your-gemini-api-key
```

### 3. Run the app

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

### 4. Run tests

```bash
pytest tests/ -v
```

---

## ⚙️ Environment Variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `FLASK_ENV` | Yes | `development` | Set to `production` when deployed |
| `FLASK_SECRET_KEY` | Production | auto-generated | Secure session signing key |
| `GEMINI_API_KEY` | Yes | — | Google Gemini API key for chat and summaries |
| `DATABASE_URL` | Production | SQLite file | PostgreSQL connection string |
| `STORAGE_BACKEND` | No | `local` | `local` or `s3` |
| `VECTOR_BACKEND` | No | `chroma` | `chroma` or `pinecone` |
| `QUEUE_BACKEND` | No | `sync` | `sync` or `rq` |
| `MAX_CONTENT_LENGTH` | No | `25 MB` | Maximum upload file size |
| `AWS_ACCESS_KEY_ID` | S3 only | — | S3 access key |
| `AWS_SECRET_ACCESS_KEY` | S3 only | — | S3 secret key |
| `AWS_REGION` | S3 only | — | S3 bucket region |
| `S3_BUCKET_NAME` | S3 only | — | Bucket name for uploaded PDFs |
| `PINECONE_API_KEY` | Pinecone only | — | Pinecone API key |
| `PINECONE_INDEX_NAME` | Pinecone only | — | Existing Pinecone index name |
| `REDIS_URL` | RQ only | — | Redis connection URL for worker jobs |

---

## 🐳 Deployment

### Docker

```bash
docker build -t researchgpt .
docker run --env-file .env -p 5000:5000 researchgpt
```

### Render (Recommended)

1. Fork this repo and connect it to [Render](https://render.com).
2. Render will auto-detect `render.yaml` and create the web service + PostgreSQL database.
3. Set required environment variables (`GEMINI_API_KEY`, etc.) in the Render dashboard.
4. Deploy. The `/health` endpoint is used for health checks.

### Production Environment Example

```env
FLASK_ENV=production
FLASK_SECRET_KEY=replace-with-a-long-random-secret
GEMINI_API_KEY=your-gemini-api-key

DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE

STORAGE_BACKEND=s3
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=ap-south-1
S3_BUCKET_NAME=your-bucket

VECTOR_BACKEND=pinecone
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_INDEX_NAME=researchgpt

QUEUE_BACKEND=rq
REDIS_URL=redis://default:PASSWORD@HOST:PORT
```

### Running the Worker (for background PDF processing)

```bash
python worker.py
```

---

## 📁 Project Structure

```
ResearchGPT/
├── app.py                  # Flask application factory and routes
├── config.py               # Environment-aware configuration classes
├── extensions.py            # SQLAlchemy and LoginManager instances
├── models.py               # User, Document, ChatSession, ChatMessage models
├── rag_engine.py            # RAG pipeline: PDF → chunks → embeddings → Gemini
├── vector_store_factory.py  # Vector store backend selector (Chroma/Pinecone)
├── storage_service.py       # File storage abstraction (Local/S3)
├── jobs.py                 # Document processing jobs (sync or RQ)
├── worker.py               # RQ worker process entry point
├── gunicorn.conf.py         # Gunicorn production configuration
├── Dockerfile              # Container build instructions
├── Procfile                # Heroku/Render process definitions
├── render.yaml             # Render Blueprint for one-click deploy
├── requirements.txt        # Python dependencies
├── templates/              # Jinja2 HTML templates
│   ├── base.html           # Base layout with sidebar navigation
│   ├── home.html           # Dashboard page
│   ├── upload.html         # Paper upload page
│   ├── chat.html           # AI chat page
│   ├── login.html          # Login form
│   ├── register.html       # Registration form
│   └── errors/             # Custom error pages (404, 500)
├── static/
│   ├── css/style.css       # Application styles
│   └── js/main.js          # Client-side JavaScript
└── tests/
    ├── conftest.py         # Shared pytest fixtures
    ├── test_auth.py        # Authentication flow tests
    ├── test_upload.py      # Upload validation tests
    ├── test_api.py         # API endpoint tests
    └── test_rag.py         # RAG engine unit tests
```

---

## 🔮 Future Work

- **Google OAuth** — Social login via Google for faster onboarding
- **Chat Session Persistence** — Save and resume chat conversations across sessions
- **Multi-format Support** — Support for DOCX, TXT, and Markdown uploads
- **Real-time Processing Status** — WebSocket-based live status updates during PDF indexing
- **Rate Limiting** — API rate limiting per user to prevent abuse
- **Admin Dashboard** — System-wide analytics and user management
- **PDF Viewer** — In-app PDF rendering with highlighted source passages
- **Export Chat History** — Download conversations as Markdown or PDF

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

## 📝 Notes

- The first embedding model load takes time as sentence-transformers downloads model weights (~80 MB).
- Local uploads, SQLite data, Chroma files, virtual environments, and secrets are all ignored by git.
- For a resume demo, deploy with Pinecone (`VECTOR_BACKEND=pinecone`) to avoid local disk dependencies.
