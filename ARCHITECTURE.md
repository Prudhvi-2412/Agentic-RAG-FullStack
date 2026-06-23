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

When a user submits a query, DocuMind AI executes an advanced, multi-stage retrieval pipeline rather than a simple semantic lookup. Below is the technical architecture of the search techniques implemented in the codebase:

```mermaid
graph TD
    UserQuery[User Query] --> IntentRouter{1. QueryRouter Classification}
    
    %% GENERAL CHAT PATH
    IntentRouter -->|GENERAL_CHAT| DirectGemini[Direct Gemini Chat Stream]
    
    %% DOCUMENT QUERY PATH
    IntentRouter -->|DOCUMENT_QUERY| Condensation{2. Query Condensation}
    
    Condensation -->|Has History| Rephrase[Condense with History via LLM]
    Condensation -->|No History| RawQuery[Use Raw Query]
    
    Rephrase --> HyDE[3. HyDE: Hypothetical Document Embedding]
    RawQuery --> HyDE
    
    HyDE --> GeminiHyDE[Gemini generates hypothetical answer]
    GeminiHyDE --> FuseEmbed[4. Fused Embedding: 50% Query + 50% HyDE]
    
    FuseEmbed --> PineconeSearch[5. Pinecone Vector Search + Metadata Filter]
    PineconeSearch --> GetCandidates[Retrieve top_k * 3 dense candidates]
    
    GetCandidates --> BM25[6. Local BM25 Sparse Keyword Scoring]
    BM25 --> HybridFusion[7. Hybrid Fusion: 0.5 * Cosine + 0.5 * BM25]
    
    HybridFusion --> SortCandidates[Sort & slice top 8 candidates]
    SortCandidates --> CrossEncoder[8. Cross-Encoder LLM Reranking via Gemini]
    
    CrossEncoder --> TopK[Select top_k most relevant chunks]
    TopK --> ContextExpand[9. Sentence-Window Context Expansion]
    ContextExpand --> FetchAdjacent[Fetch adjacent c-1 & c+1 chunks from Pinecone]
    
    FetchAdjacent --> GroundedGen[10. Grounded Generation: Context + LLM Chat Stream]
```

### Detailed Sequence Diagram

The interaction sequence between the frontend, backend service singletons, and external APIs during a document query:

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant App as React Frontend
    participant API as FastAPI Backend (chat route)
    participant Router as QueryRouter
    participant Embed as EmbeddingService
    participant VS as VectorStoreService
    participant Reranker as GeminiReranker
    participant Pine as Pinecone DB
    participant Gem as Gemini 2.5 Flash
    
    User->>App: Submits Chat Query (e.g., active filters list)
    App->>API: POST /api/query { query, filters, history }
    API->>API: Initialize EventSource SSE Stream
    
    API->>Router: classify_query(query)
    Router-->>API: Return query_type (DOCUMENT_QUERY)
    API-->>App: SSE event: metadata { query_type: DOCUMENT_QUERY }
    
    opt Has History Context
        API->>Router: condense_query(query, history)
        Router-->>API: Return standalone condensed query
    end
    
    API->>VS: similarity_search(condensed_query, top_k, filters)
    
    %% HyDE Generation
    VS->>Embed: get_query_embedding(query, use_hyde=True)
    Embed->>Gem: generate_hyde_text(query)
    Gem-->>Embed: Hypothetical answer paragraph
    Embed->>Embed: Fuse query & HyDE embeddings (768d)
    
    %% Vector Query
    VS->>Pine: index.query(fused_vector, top_k*3, metadata_filter)
    Pine-->>VS: Top candidates with Cosine scores
    
    %% BM25 & Hybrid
    VS->>VS: calculate_bm25_scores(query, candidate_texts)
    VS->>VS: Combine scores: 0.5 * Cosine + 0.5 * BM25
    VS->>VS: Sort & slice to top 8 candidates
    
    %% LLM Reranker
    VS->>Reranker: rerank(query, top_8_candidates, top_k)
    Reranker->>Gem: generate_content(Select top_k IDs)
    Gem-->>Reranker: JSON response {"ranked_ids": [...]}
    Reranker-->>VS: Re-sorted top_k chunks
    
    %% Sentence Window
    VS->>Pine: index.fetch(prev_ids & next_ids)
    Pine-->>VS: Preceding & succeeding context text
    VS->>VS: Stitch context (c-1 + current + c+1)
    
    VS-->>API: Return expanded top_k chunks
    API-->>App: SSE event: sources { retrieved sources metadata }
    
    %% Generation
    API->>Gem: generate_content_stream(Prompt + Reranked Context)
    
    loop Stream response
        Gem-->>API: Yield word tokens
        API-->>App: SSE event: token { text }
    end
    API-->>App: SSE event: complete {}
```

---

### 🔍 Search Techniques Breakdown & Implementation

#### 1. Zero-Shot Intent-Based Routing (`router.py`)
Intercepts queries before hitting vector databases to optimize latency and costs. Using `gemini-2.5-flash` with temperature `0.0`, queries are classified into:
*   `DOCUMENT_QUERY`: Triggers RAG pipeline (e.g. *"Summarize section 4 of the guidelines"*).
*   `GENERAL_CHAT`: Direct stream from Gemini, bypassing database lookups entirely (e.g. *"Write a python quicksort function"*).

#### 2. Hypothetical Document Embeddings (HyDE) (`embedding.py`)
To bridge the vocabulary and conceptual gap between queries and target passages, the system uses HyDE query expansion. The model generates a hypothetical paragraph answer to the user's query. Both the raw query and hypothetical paragraph are embedded using `gemini-embedding-001`, and combined element-wise:
$$\vec{E}_{\text{final}} = 0.5 \cdot \vec{E}_{\text{query}} + 0.5 \cdot \vec{E}_{\text{hypothetical}}$$
*This allows the vector database search to match document-to-document representations, significantly improving semantic retrieval accuracy.*

#### 3. Metadata Filtering (`vectorstore.py`)
Limits the search boundary using Pinecone's metadata keys. Checkboxes selected on the UI translate to database-level constraints:
```python
filter = {"filename": {"$in": selected_filenames}}
```
*This allows multi-document isolation, ensuring users search only the files they explicitly select.*

#### 4. Dense-Sparse Hybrid Search (`vectorstore.py`)
Vector databases excel at capturing semantic synonyms but struggle with exact keywords, codes, or formulas. We resolve this by calculating local BM25 keyword matching scores for the dense candidates, and performing Reciprocal Rank/Score Fusion:
$$\text{Score}_{\text{hybrid}} = 0.5 \cdot \text{Score}_{\text{CosineSimilarity}} + 0.5 \cdot \text{Score}_{\text{BM25Normalized}}$$
*Dense search retrieves top candidates conceptually, and sparse BM25 scores highlight the ones matching the exact keywords.*

#### 5. Cross-Encoder LLM Reranking (`reranker.py`)
Rather than relying solely on mathematical vector distance calculations, candidate chunks are evaluated contextually. The top 8 candidates are presented to `gemini-2.5-flash` as a Cross-Encoder Reranker, which selects the top `top_k` chunks that directly address the user's query intent.
*This filters out false-positive vector matches and places the most relevant details at the beginning of the context block.*

#### 6. Sentence-Window Context Expansion (`vectorstore.py`)
To keep vector retrieval highly specific but generation context-rich, documents are chunked into small semantic units (750 chars). During retrieval, once a chunk is selected, the backend extracts the preceding and succeeding chunk IDs using the structured index schema:
$$\text{IDs} = [id_{\text{chunk} - 1}, id_{\text{chunk}}, id_{\text{chunk} + 1}]$$
It fetches these surrounding paragraphs in a single batch call to Pinecone, stitching the texts together before feeding them to Gemini.
*This solves the core RAG dilemma: retrieving precise segments for embedding matching while providing broad context for LLM comprehension.*


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
