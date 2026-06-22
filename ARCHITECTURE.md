# DocuMind AI Architecture Walkthrough

This document outlines the technical design, data flows, and UI wireframes of the DocuMind AI platform.

---

## 🗺️ System Overview

The core architecture follows a decoupled Micro-RAG layout. The frontend operates as an interactive workspace while the backend FastAPI server processes files, queries Pinecone Serverless indices, and manages Gemini streams.

```mermaid
graph TD
    Client[React App / Client] -->|1. Upload Document| API[FastAPI Server]
    Client -->|2. Send Query| API
    
    API -->|Ingest: Render Page Images| Vision[Gemini Vision API]
    Vision -->|Transcribed Text| Chunk[Recursive Splitter]
    Chunk -->|Text Chunks| Embed[Gemini Embeddings API]
    Embed -->|768d Vectors| DB[(Pinecone DB)]
    
    API -->|Query: Router Classify| Routing{Query Router}
    Routing -->|GENERAL_CHAT| Direct[Gemini Generative API]
    Routing -->|DOCUMENT_QUERY| RAG[Hybrid Search / Reranker]
    
    RAG -->|Similarity Search + Filters| DB
    RAG -->|Reranked Context Chunks| Direct
    
    Direct -->|SSE Stream Response| Client
```

---

## 📥 Ingestion Pipeline Flow

When a user drops a document (e.g., a PDF) into the workspace sandbox, it flows through these stages:

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant App as React Frontend
    participant API as FastAPI Backend
    participant Fitz as PyMuPDF
    participant Gem as Gemini Vision (2.5)
    participant Pine as Pinecone DB
    
    User->>App: Drag & Drop PDF
    App->>API: POST /api/upload (File Bytes)
    API->>Fitz: Open Document
    loop Each Page
        API->>Fitz: Render Page to PNG Pixmap
        API->>Gem: generate_content(PNG, "Extract Visual Layout")
        Gem-->>API: Yields layout markdown, charts, signatures
        API->>API: Append layout markdown to raw text
    end
    API->>API: Split pages text (Recursive Splitter)
    API->>Gem: Generate Embeddings (768d)
    API->>Pine: Upsert vectors & metadata (document_id, filename, text)
    API-->>App: Return 200 OK (status: indexed)
    App-->>User: Update Document List (Interactive Checkbox)
```

---

## 💬 Query Routing & Retrieval Pipeline

When a user submits a query:

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant App as React Frontend
    participant API as FastAPI Backend
    participant Router as QueryRouter
    participant Pine as Pinecone DB
    participant Gem as Gemini Chat (2.5)
    
    User->>App: Submits Chat Query (Optional filters list)
    App->>API: POST /api/query { query, filters }
    API->>API: Initialize EventSource SSE Stream
    API->>Router: Classify intent
    Router-->>API: Return query_type (GENERAL_CHAT | DOCUMENT_QUERY)
    API-->>App: SSE event: metadata (query_type)
    
    alt query_type is DOCUMENT_QUERY
        API->>Pine: similarity_search(query_vector, filters)
        Pine-->>API: Return top_k * 3 candidate chunks
        API->>API: Compute Keyword Overlap scores
        API->>API: Sort by Combined Score (0.7 * Cosine + 0.3 * Overlap)
        API-->>App: SSE event: sources (top_k chunks)
        API->>Gem: generate_content_stream(query + reranked context)
    else query_type is GENERAL_CHAT
        API->>Gem: generate_content_stream(query directly)
    end
    
    loop Stream response
        Gem-->>API: Yield word tokens
        API-->>App: SSE event: token { text }
    end
    API-->>App: SSE event: complete {}
```

---

## 🔊 Multilingual Text-to-Speech (TTS) Pipeline

When a user clicks "Read Aloud" on any assistant response:

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant App as React Frontend (useAudio)
    participant API as FastAPI Backend (tts route)
    participant Service as TTSService
    participant Cache as Local TTS Cache (MP3s)
    participant MS as MS Edge Neural TTS API
    
    User->>App: Click Speaker Icon (Read Aloud)
    App->>API: POST /api/tts { text, language, gender, rate }
    API->>Service: stream_audio(text, lang, gender, rate)
    Service->>Service: Compute MD5 Hash of settings
    alt Cache file exists (HIT)
        Service->>Cache: Read cached file bytes
        Cache-->>Service: Audio stream
        Service-->>API: Stream cache chunks
        API-->>App: Audio/mpeg binary stream
    else Cache file missing (MISS)
        Service->>MS: Initiate async stream (edge_tts)
        loop Stream synthesis chunks
            MS-->>Service: Chunk bytes
            Service->>Cache: Write chunk to disk
            Service-->>API: Yield chunk
            API-->>App: Audio/mpeg binary stream
        end
    end
    App->>App: Play binary stream in HTML5 Audio
    App-->>User: Hear spoken voice (selected dialect)
```

---

## 🎤 Speech-to-Text (STT) Voice Input Flow

When a user clicks the Microphone button to dictate their query:

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant App as React Frontend (ChatPanel)
    participant WebSpeech as Web Speech API (Browser Native)
    
    User->>App: Click Microphone (🎤) button
    App->>WebSpeech: Initialize SpeechRecognition (continuous=false)
    App->>WebSpeech: Set recognition locale (e.g., ta-IN, de-DE, es-ES)
    App->>WebSpeech: start()
    WebSpeech-->>App: Listening state active (pulsing indicator)
    User->>App: Speak into microphone
    App->>WebSpeech: Audio input
    WebSpeech->>WebSpeech: Transcribe voice to text local engine
    WebSpeech-->>App: onresult(transcript text)
    App->>App: Append transcript to chat input field
    WebSpeech-->>App: onend() (deactivate listening state)
```

---

## 🎨 UI Wireframe Layout

The divided modular frontend displays a split-screen dashboard workspace:

```
+----------------------------------------------------------------------------------+
|  [Sparkles] DocuMind AI           [Home]   [Workspace]                 v1.0.0 [] |
+----------------------------------------------------------------------------------+
|  SIDEBAR (320px)       |  CHAT INTERFACE (Flexible Width)  | CITATIONS PANEL (320px) |
|                        |                                   |                         |
|  [ Ingest Document ]   |  Query Session 1                  | [BookMarked] Sources    |
|                        |  Gemini Ingress Connected         |                         |
|  CONVERSATIONS         |  +-----------------------------+  | +---------------------+ |
|  [Msg] Session 1       |  | User: What is Section 4?    |  | | policy_terms.pdf    | |
|  [Msg] Session 2       |  +-----------------------------+  | | Page 2 | 87.5% Match| |
|                        |  | AI: According to Sec 4...   |  | | "Extract snippet"   | |
|  DOCUMENT INDEX        |  +-----------------------------+  | +---------------------+ |
|  Select files to filter|                                   |                         |
|  [x] policy_terms.pdf  |  [ Ask a question...        ] [>] | | policy_guide.docx   | |
|  [ ] guidelines.md     |  [Info] Gemini Agent routes query | | Page 1 | 64.2% Match| |
|                        |                                   | +---------------------+ |
|  [AI] Dev Mode     [S] |                                   |                         |
+----------------------------------------------------------------------------------+
```

*   **Header**: Coordinates views switcher between landing page and workspace.
*   **Sidebar (`components/Sidebar.tsx`)**: Controls PDF document loading upload state, chat sessions, and checkboxes to isolate metadata filters.
*   **Chat Panel (`components/ChatPanel.tsx`)**: Streams conversational turns, displays reasoning classification pathways, manages inputs, and integrates audio player components.
*   **Voice Controller (`components/VoiceController.tsx`)**: Floating menu dropdown managing speech options (TTS voice dialect, gender, rate, and STT locale).
*   **Citations Panel (`components/CitationsPanel.tsx`)**: Shows active source citations matching the retrieved vectors.
