# DocuMind AI — Agentic Multimodal RAG Platform

<div align="center">

[![Live Demo](https://img.shields.io/badge/🌐%20Live%20Demo-Render-4f46e5?style=for-the-badge)](https://agentic-rag-fullstack.onrender.com/)
[![Backend](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi)](https://agentic-rag-fullstack.onrender.com/)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.0.0-brightgreen?style=for-the-badge)](#)

**🌐 Live Demo:** [https://agentic-rag-fullstack.onrender.com/](https://agentic-rag-fullstack.onrender.com/)

</div>

---

DocuMind AI is a **production-grade, enterprise-ready Agentic Retrieval-Augmented Generation (RAG) platform**. Upload PDF, DOCX, Markdown, or TXT documents and interact with them using layout-aware visual grounding, intent-based agentic routing, selective document filtering, hybrid vector search, and real-time streaming — all powered by **Google Gemini 2.5 Flash** and **Pinecone Serverless**.

---

## 📋 Table of Contents

- [Why DocuMind vs. Standard AI Chat?](#-why-documind-vs-standard-ai-chat)
- [Key Features](#-key-features)
- [API Integration Architecture](#-api-integration-architecture)
- [Frontend Features](#-frontend-features)
- [Technology Stack](#️-technology-stack)
- [Repository Structure](#-repository-structure)
- [Quick Start](#️-quick-start)
- [Deployment (Render)](#-deployment-render)
- [Environment Variables](#-environment-variables)
- [Architecture Deep-Dive](#-architecture--deep-dive)

---

## 🆚 Why DocuMind vs. Standard AI Chat?

This is the core differentiator. The frontend landing page (`LandingView.tsx`) explicitly highlights these distinctions in the **"Next-Generation Document Intelligence"** comparison section.

| Feature | Standard AI Chat (e.g., ChatGPT file upload) | DocuMind AI (This Project) |
|---|---|---|
| **Context Scale** | Hard token limit — large PDFs get truncated or hallucinated | Infinite scale: chunks & indexes full document collection; retrieves only relevant segments |
| **Visual/Table Understanding** | Flat text extraction — tables become garbled, charts are lost | Gemini Vision OCR per page — tables → Markdown, diagrams → described, layout preserved |
| **Source Attribution** | Vague or fabricated references | Deterministic page-level citations with exact filename, page number, and confidence % |
| **Query Routing** | Every query hits the same model pipeline regardless of type | Zero-shot intent classification routes chat vs. document queries separately |
| **Multi-Document Filtering** | Query runs across all uploaded files uniformly | Checkbox-based metadata filtering scopes Pinecone search to user-selected files |
| **Data Privacy** | Files may be stored or used in training data by the provider | Isolated private Pinecone namespace + Supabase session — never shared or trained on |
| **Search Quality** | Pure semantic similarity only | **Hybrid search**: 70% dense cosine similarity + 30% keyword overlap reranking |
| **Authentication** | N/A | Supabase Auth — Email/Password + Google OAuth SSO |
| **Response Delivery** | Full response wait (blocking) | Real-time token streaming via **Server-Sent Events (SSE)** |
| **CI/CD** | N/A | GitHub Actions pipeline + Render auto-deploy on merge |

---

## 🚀 Key Features

### 1. 🔭 Multimodal Vision Ingestion (Gemini Vision)
Rather than extracting raw flat text, DocuMind uses **Gemini 2.5 Flash** to render each PDF page as a 150 DPI PNG image and analyze its full visual layout:
- **Tables** → transcribed into clean Markdown format
- **Charts, Diagrams** → described semantically for conceptual indexing
- **Headers, Signatures, Handwriting** → identified and preserved
- Extracted visual layout is **appended to the raw text** before chunking, enriching vector context

### 2. 🧠 Intent-Based Agentic Routing (QueryRouter)
A lightweight zero-shot Gemini classifier intercepts every incoming query *before* it hits the vector store:
- **`GENERAL_CHAT`** — greetings, general knowledge → directly streams from Gemini, bypassing Pinecone entirely (saves latency + API cost)
- **`DOCUMENT_QUERY`** — document-context questions → triggers full Pinecone semantic search pipeline

The routing decision is **streamed back to the frontend** as an SSE `metadata` event, displayed as a visual indicator in the Chat Panel.

### 3. 🔍 Selective Metadata Filtering
Users select specific uploaded documents via **interactive checkboxes** in the Sidebar (`Sidebar.tsx`). Pinecone restricts the similarity search scope using metadata tags:
```python
filter={"filename": {"$in": selected_filenames}}
```
Leave all checkboxes unchecked to search across your entire document index.

### 4. ⚡ Dense-Sparse Hybrid Search Reranking
Candidate chunks from Pinecone are re-ranked using a combined scoring formula:

```
Relevance Score = 0.7 × Cosine Similarity (dense) + 0.3 × Keyword Overlap (sparse)
```

- **Dense**: 768-dimensional `text-embedding-004` cosine similarity
- **Sparse**: Normalized keyword overlap frequency across query terms
- Retrieves `top_k × 3` candidates from Pinecone, then reranks and returns the best `top_k`

### 5. 📡 SSE Streaming & Citations Panel
Real-time token streaming via **Server-Sent Events (SSE)** — no waiting for full response:

The stream emits **4 ordered event types**:
| SSE Event | Payload | Purpose |
|---|---|---|
| `metadata` | `{ query_type }` | Routing path indicator (GENERAL_CHAT / DOCUMENT_QUERY) |
| `sources` | `{ sources: [...] }` | Retrieved context chunks with page refs |
| `token` | `{ text }` | Streamed response word tokens |
| `complete` | `{ status }` | Stream finished / error |

The **Citations Panel** (`CitationsPanel.tsx`) renders source attributions alongside responses:
- Source document filename
- Exact physical page number
- Combined relevance confidence percentage
- Context snippet preview

### 6. 🔐 Supabase Authentication
Full production auth integration (`AuthModal.tsx`):
- **Email/Password** sign-up and sign-in with form validation
- **Google OAuth SSO** via `supabase.auth.signInWithOAuth()`
- Session-aware Header (`Header.tsx`) — shows user email avatar when logged in, `Sign In` button when not
- Persists auth state across page reloads via Supabase session listener

### 7. 📚 Multi-Session Chat Management
Persistent chat workspace with full session management (`Sidebar.tsx`):
- Create unlimited named **conversation sessions**
- Switch between sessions — each maintains its own message history
- Delete individual sessions with hover-reveal trash icon
- Default "Ikigai" demo document pre-loaded in the index for immediate exploration

### 8. 🗑️ Document Lifecycle Management
Full document CRUD from the Sidebar:
- Upload documents via **drag-and-drop** or **file browser** (LandingView `onDrop` handler)
- View indexed document count (**chunk vectors** stored per file)
- Delete a document from the vector index — triggers `VectorStoreService.delete_document()` which purges all Pinecone vectors matching that `document_id`
- Demo documents show a `Demo` badge label

### 9. 🌙 Dark Mode Toggle
Full system-level dark/light mode toggle via `Header.tsx`:
- Persisted across navigation between Landing and Dashboard views
- Uses Tailwind's `dark:` class system applied at root level
- Sun/Moon icon toggle with amber/slate color theming

### 10. 🔊 Multilingual Text-to-Speech (TTS) Narration
High-fidelity neural speech synthesis built into the assistant response bubbles:
- **Languages supported**: European (German, French, Spanish, Italian, Portuguese) and Indian regional (Tamil, Telugu, Malayalam, Kannada, Marathi) plus English.
- **Dynamic Controls**: Select speed/rate (0.8x to 1.5x) and voice gender (Male/Female neural models).
- **Latency Optimization**: Streams audio chunks via FastAPI `StreamingResponse` for immediate playback.
- **Scale Caching**: Automatically hashes text and voice configurations to save and serve cached MP3 files on repeated requests, reducing external network overhead.

### 11. 🎤 Hands-Free Speech-to-Text (STT) Input
Voice typing capabilities integrated directly inside the conversational input toolbar:
- Uses the standard web-browser **Web Speech API** for instant, client-side transcriptions without any extra API keys.
- Auto-localizes speech recognition to match the selected target language (e.g. `ta-IN` for Tamil, `de-DE` for German).
- Pulsing microphone status indicator and typing overlays.

### 12. 🚀 CI/CD Pipeline (GitHub Actions + Render)
Automated deployment pipeline via `.github/workflows/`:
- Triggers on `push` to `main` and on pull requests
- Runs backend Python tests and frontend TypeScript build validation
- Render auto-deploys on successful merge via `render.yaml` manifest
- **PR preview deployments** enabled for frontend static site

---

## 🔌 API Integration Architecture

DocuMind integrates **4 external API services**:

### Google Gemini API (`google-genai` SDK)
Used in 3 distinct roles:

| Role | Service | Model | Purpose |
|---|---|---|---|
| **Vision OCR** | `DocumentProcessor` | `gemini-2.5-flash` | Analyze PDF page images, extract tables/charts as markdown |
| **Intent Classifier** | `QueryRouter` | `gemini-2.5-flash` | Zero-shot query type classification |
| **Chat Generation** | `ChatService` | `gemini-2.5-flash` | Context-grounded streaming response generation |

```python
# All services use the unified google-genai Client
from google import genai
client = genai.Client(api_key=GEMINI_API_KEY)

# Streaming response
client.models.generate_content_stream(model=model_name, contents=prompt)

# Vision analysis
client.models.generate_content(model=model_name, contents=[image_part, text_prompt])
```

### Pinecone Serverless Vector DB
```python
from pinecone import Pinecone, ServerlessSpec

pc = Pinecone(api_key=PINECONE_API_KEY)
# Auto-creates index if missing (768d, cosine, AWS us-east-1)
index.upsert(vectors=[(id, embedding, metadata)])
index.query(vector=query_embedding, filter={"filename": {"$in": [...]}})
index.delete(filter={"document_id": {"$eq": doc_id}})
```

### Google Text Embeddings API
```python
# EmbeddingService — uses text-embedding-004 (768 dimensions)
client.models.embed_content(
    model="text-embedding-004",
    contents=[text],
    config=EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
)
```

### Supabase (Auth + BaaS)
```typescript
// Frontend — supabaseClient.ts
import { createClient } from '@supabase/supabase-js'
const supabase = createClient(VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY)

// Email/Password auth
supabase.auth.signInWithPassword({ email, password })

// Google OAuth
supabase.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: origin } })
```

---

## 🎨 Frontend Features

The frontend is built with **React + TypeScript + Vite + Tailwind CSS** and consists of 6 modular components:

| Component | File | Features |
|---|---|---|
| **Header** | `Header.tsx` | Logo nav, Home/Workspace toggles, auth state (Sign In / user avatar + Logout), dark mode toggle, version badge |
| **Landing Page** | `LandingView.tsx` | Hero section, drag-and-drop upload zone, 4-card feature grid, "DocuMind vs Standard AI" 5-card comparison section |
| **Sidebar** | `Sidebar.tsx` | Ingest Document button with upload spinner, Conversations list with New/Delete, Document Index with checkboxes + vector counts + Demo badge + delete |
| **Chat Panel** | `ChatPanel.tsx` | Session title, SSE streaming message display, routing indicator badge, Markdown rendering, message input |
| **Citations Panel** | `CitationsPanel.tsx` | Source attribution cards with filename, page number, relevance %, context snippet |
| **Auth Modal** | `AuthModal.tsx` | Email/Password form, Google OAuth button, Sign Up/Sign In toggle, error/success alerts |

### Landing Page — "Next-Gen vs Standard LLM" Section
The landing page explicitly surfaces the key differentiators in a 3+2 bento-grid card layout:
1. **Unbounded Context Scale** — no token truncation
2. **Visual & Structural Grounding** — layout OCR vs. flat text
3. **Deterministic Source Mappings** — exact page citations vs. hallucinated refs
4. **Intent-Based Routing** — smart bypass of vector search
5. **Private Sandbox Data Security** — isolated namespace vs. public LLM training

---

## 🛠️ Technology Stack

### Frontend
| Technology | Purpose |
|---|---|
| React 18 + TypeScript | UI framework |
| Vite | Build tool + dev server |
| Tailwind CSS | Utility-first styling + dark mode |
| Lucide React | Icon library |
| Supabase JS Client | Auth SDK + session management |
| EventSource API | SSE streaming from backend |
| Web Speech API | Client-side Speech-to-Text translation (browser native) |

### Backend
| Technology | Purpose |
|---|---|
| FastAPI | Async REST API + SSE streaming |
| PyMuPDF (`fitz`) | PDF page rendering to PNG pixmaps |
| `python-docx` | Word document paragraph extraction |
| LangChain Text Splitters | Recursive character chunking (750 tokens / 150 overlap) |
| Pydantic V2 | Request/response schema validation |
| `python-dotenv` | Environment variable loading |
| `edge-tts` | Async Microsoft Azure Neural TTS engine integration |

### AI & Cloud APIs
| Service | SDK | Role |
|---|---|---|
| Google Gemini 2.5 Flash | `google-genai` | Vision OCR, query routing, chat generation |
| Google text-embedding-004 | `google-genai` | 768-dimensional dense vector embeddings |
| Pinecone Serverless | `pinecone` | Vector storage, cosine similarity search, metadata filtering |
| Supabase | `supabase-js` | User authentication, Google OAuth |
| MS Edge Neural Voices | `edge-tts` | Multilingual high-fidelity audio synthesis |

### DevOps
| Tool | Purpose |
|---|---|
| GitHub Actions | CI/CD pipeline (lint, build, test on PR) |
| Render | Cloud hosting — FastAPI web service + React static site |
| `render.yaml` | Infrastructure-as-Code deployment manifest |

---

## 📁 Repository Structure

```
Agentic-RAG-FullStack/
├── .github/
│   └── workflows/           # GitHub Actions CI/CD pipeline definitions
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py    # Settings loader (reads .env via pydantic)
│   │   │   └── logging.py   # Structured logging setup
│   │   ├── models/          # Pydantic models (chat.py, document.py, tts.py)
│   │   ├── routes/
│   │   │   ├── chat.py      # POST /api/query — SSE streaming endpoint
│   │   │   ├── document.py  # POST /api/upload, GET /api/documents, DELETE /api/documents/{id}
│   │   │   └── tts.py       # POST /api/tts — Speech synthesis stream endpoint
│   │   ├── services/
│   │   │   ├── chat.py      # ChatService — SSE orchestrator & Gemini chat stream
│   │   │   ├── document.py  # DocumentProcessor — PDF/DOCX/TXT extraction + Gemini Vision
│   │   │   ├── embedding.py # EmbeddingService — text-embedding-004 via google-genai
│   │   │   ├── router.py    # QueryRouter — zero-shot intent classifier
│   │   │   ├── tts.py       # TTSService — edge-tts synthesis + caching engine
│   │   │   └── vectorstore.py # VectorStoreService — Pinecone upsert, hybrid search, delete
│   │   └── main.py          # FastAPI app + startup DI + CORS config
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AuthModal.tsx     # Sign In/Sign Up modal + Google OAuth
│   │   │   ├── ChatPanel.tsx     # Streaming chat interface with voice integrations
│   │   │   ├── CitationsPanel.tsx # Source attribution panel
│   │   │   ├── Header.tsx        # Navigation header + dark mode + auth state
│   │   │   ├── LandingView.tsx   # Landing page hero + feature cards + comparison section
│   │   │   ├── Sidebar.tsx       # Document management + chat sessions
│   │   │   └── VoiceController.tsx # Voice panel settings (TTS settings + STT settings)
│   │   ├── hooks/
│   │   │   ├── useAuth.ts
│   │   │   ├── useDocuments.ts
│   │   │   ├── useChat.ts
│   │   │   └── useAudio.ts       # Audio controls state & WebSpeech recognition manager
│   │   ├── types/               # TypeScript interface definitions
│   │   ├── supabaseClient.ts    # Supabase client initialization
│   │   ├── App.tsx              # Root orchestrator — view routing + state management
│   │   └── main.tsx             # React DOM entry point
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   └── package.json
├── notebooks/                   # Exploration / testing Jupyter notebooks
├── source/                      # Additional source materials
├── supabase_schema.sql          # Supabase database schema (if used for document metadata)
├── render.yaml                  # Render deployment manifest (IaC)
├── ARCHITECTURE.md              # Data flow diagrams + Mermaid sequence charts
└── README.md
```

---

## ⚙️ Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- A [Google AI Studio](https://aistudio.google.com/) API key (free tier works)
- A [Pinecone](https://www.pinecone.io/) account (free serverless tier)
- A [Supabase](https://supabase.com/) project (free tier)

### 1. Clone & Configure Environment

```bash
git clone <your-repo-url>
cd Agentic-RAG-FullStack
```

Create `backend/.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX_NAME=documind
GEMINI_MODEL_NAME=gemini-2.5-flash
```

Create `frontend/.env`:
```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
VITE_BACKEND_URL=http://localhost:8000
```

### 2. Run Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
./venv/Scripts/activate     # Windows PowerShell
source venv/bin/activate    # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Start FastAPI dev server
uvicorn app.main:app --reload --port 8000
```

Backend is live at `http://localhost:8000`  
Interactive API docs: `http://localhost:8000/docs`

### 3. Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## ☁️ Deployment (Render)

The project includes a `render.yaml` for one-click deployment on [Render](https://render.com/):

```yaml
# Two services are auto-provisioned:
# 1. FastAPI Backend — Python Web Service (port $PORT)
# 2. React Frontend — Static Site (dist/ folder, SPA rewrite)
```

**Steps:**
1. Push repository to GitHub
2. Connect repo to Render → "New Blueprint"
3. Set secret environment variables in Render dashboard:
   - `GEMINI_API_KEY`, `PINECONE_API_KEY` (backend)
   - `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` (frontend)
4. `VITE_BACKEND_URL` is automatically injected from the backend service host

**PR Preview Deployments** are enabled — every pull request gets its own preview URL.

---

## 🔑 Environment Variables

| Variable | Service | Required | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | Backend | ✅ | Google AI Studio API key for Gemini Vision + Chat + Embeddings |
| `PINECONE_API_KEY` | Backend | ✅ | Pinecone API key for vector index |
| `PINECONE_INDEX_NAME` | Backend | ✅ | Pinecone index name (default: `documind`) |
| `GEMINI_MODEL_NAME` | Backend | ✅ | Gemini model (default: `gemini-2.5-flash`) |
| `VITE_SUPABASE_URL` | Frontend | ✅ | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Frontend | ✅ | Supabase public anonymous key |
| `VITE_BACKEND_URL` | Frontend | ✅ | Backend API URL (auto-injected on Render) |

---

## 📘 Architecture & Deep-Dive

For detailed Mermaid data flow diagrams, ingestion pipeline sequences, query routing sequences, and UI wireframes, see the **[ARCHITECTURE.md](ARCHITECTURE.md)** guide.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">
Built with ❤️ using Google Gemini, Pinecone, FastAPI, React, and Supabase.
</div>
