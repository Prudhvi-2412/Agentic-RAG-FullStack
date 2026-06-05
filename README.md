# DocuMind AI — Agentic Multimodal RAG Platform

DocuMind AI is a production-grade, enterprise-ready Agentic Retrieval-Augmented Generation (RAG) platform. It allows users to upload documents (PDF, DOCX, Markdown, TXT) and interact with them using layout-aware grounding, intent-based query routing, selective document filtering, and hybrid search.

---

## 🚀 Key Features

### 1. Multimodal Vision Ingestion (Gemini Vision)
Rather than extracting raw unstructured text from PDFs, DocuMind uses **Gemini 2.5 Flash** to analyze layout images. It transcribes visual tables into clean Markdown tables, describes complex charts, diagrams, and preserves structural layouts for deep conceptual indexing.

### 2. Intent-Based Agentic Routing
A lightweight zero-shot classifier intercepts incoming queries and routes them:
*   **GENERAL_CHAT**: Simple greetings or general knowledge questions bypass Pinecone vector stores, cutting down lookup latency and API expense.
*   **DOCUMENT_QUERY**: Context-sensitive questions trigger Pinecone semantic search, drawing attributions from matching indexes.

### 3. Selective Metadata Filtering
Users can select specific uploaded documents via interactive checkboxes in the UI. Pinecone restricts the semantic search scope instantly using metadata tags:
`filter={"filename": {"$in": selected_filenames}}`

### 4. Dense-Sparse Hybrid Search Reranking
Combines semantic search vectors (dense cosine similarity) with a keyword overlap matching algorithm (sparse simulation) to rank chunks:
$$\text{Relevance Score} = 0.7 \times \text{Cosine Similarity} + 0.3 \times \text{Keyword Overlap}$$
This guarantees exact search queries (e.g., specific terms, product IDs, section tags) are matched perfectly without losing semantic meaning.

### 5. SSE Streaming & Attributions Panel
Real-time token streaming using Server-Sent Events (SSE). Source citations are shown on the side panel detailing:
*   Original chunk content snippet.
*   Source document name and exact physical page number.
*   Combined confidence/relevance percentage.

---

## 🛠️ Technology Stack

*   **Frontend**: React, Vite, TypeScript, Tailwind CSS, Lucide Icons.
*   **Backend**: FastAPI, PyMuPDF, Pydantic V2, LangChain-Text-Splitters.
*   **AI/Vector Databases**: Google GenAI SDK (`google-genai`), Pinecone Vector DB (Serverless).

---

## 📁 Repository Structure

```
Agentic-RAG-FullStack/
├── backend/
│   ├── app/
│   │   ├── core/           # Config and settings (.env loaders)
│   │   ├── models/         # Pydantic schema declarations
│   │   ├── routes/         # FastAPI endpoints (chat routing, uploads)
│   │   ├── services/       # Business logic (Gemini models, vector stores, chunkers)
│   │   └── main.py         # Application entrypoint & Dependency Injection
│   ├── requirements.txt
│   └── .env
└── frontend/
    ├── src/
    │   ├── components/     # Subdivided UI components (Sidebar, Chat, Citations)
    │   ├── types/          # TypeScript interface models
    │   ├── App.tsx         # Root orchestrator
    │   └── main.tsx
    ├── tailwind.config.js
    └── package.json
```

---

## ⚙️ Quick Start

### 1. Clone & Set Environment variables
Create a `.env` file inside `backend/`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX_NAME=documind
GEMINI_MODEL_NAME=gemini-2.5-flash
```

### 2. Run Backend
```bash
cd backend
python -m venv venv
./venv/Scripts/activate     # Windows
source venv/bin/activate    # Linux/Mac
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Run Frontend
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 📘 Architecture & Deep-Dive
For a detailed look at data flow, backend architecture, and design wireframes, check out the [ARCHITECTURE.md](ARCHITECTURE.md) guide.

## 📄 License
This project is licensed under the [MIT License](LICENSE).
