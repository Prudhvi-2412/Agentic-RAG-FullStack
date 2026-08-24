PART_3 = r'''
# Part 3 - Complete Architecture

## The whole system on one page

~~~
                                  BROWSER (React 18 + TypeScript + Vite + Tailwind)
   +-------------------------------------------------------------------------------------+
   |  Header    LandingView    Sidebar    ChatPanel    CitationsPanel    AuthModal        |
   |  hooks:  useAuth      useDocuments      useChat      useAudio                        |
   +-------------------------------------------------------------------------------------+
        |                          |                                    |
        | (1) auth + chat history  | (2) upload / query / tts           | (3) mic
        |     + document list      |     with Bearer <access_token>     |     (browser API)
        v                          v                                    v
  +--------------+     +-----------------------------------+     +------------------+
  |  SUPABASE    |     |     FastAPI  (Render web svc)     |     | Web Speech API   |
  |  - Auth      |     |                                   |     | (client-side STT)|
  |  - Postgres  |     |  routes/  -> thin, validate+auth  |     +------------------+
  |    documents |     |  models/  -> pydantic schemas     |
  |    chat_...  |     |  services/-> the actual logic     |
  |    messages  |     |  core/    -> config, auth, retry  |
  |  - RLS on    |     +-----------------------------------+
  +--------------+          |            |             |
         ^                  |            |             |
         | JWKS             |            |             |
         | (public keys)    v            v             v
         |          +-------------+ +----------+ +-------------+
         +----------|   GEMINI    | | PINECONE | |  edge-tts   |
                    | vision      | | serverless| | (MS neural |
                    | routing     | | 768-dim   | |  voices)   |
                    | embeddings  | | cosine    | +-------------+
                    | reranking   | | metadata  |
                    | generation  | |  filter   |
                    +-------------+ +----------+
~~~

Three things to notice, because interviewers ask about all three:

1. **The browser talks to Supabase directly.** There is no backend endpoint for "list my
   documents" or "load my chat history". The React app queries Supabase Postgres itself,
   and Supabase Row Level Security enforces that you only get your own rows.
2. **The backend never talks to Supabase Postgres.** It only *verifies tokens Supabase
   issued*, using the public keys from Supabase's JWKS endpoint. The backend is stateless
   with respect to user data.
3. **Only the backend holds the expensive secrets.** The Gemini and Pinecone API keys never
   reach the browser. That is the whole reason upload and query go through FastAPI rather
   than straight from React.

## The ingestion path, box by box

~~~
  File (PDF/DOCX/TXT/MD)
        |
        v
  [1] POST /api/upload  ---- require_user_id() -> 401 if no valid token
        |
        v
  [2] Validation: filename sanitised, extension allow-list, <=25 MB, non-empty
        |
        v
  [3] DocumentProcessor.process_file()   (runs in a worker thread)
        |
        +-- PDFParser: batches of 8 pages
        |     - PyMuPDF page.get_text()          (serial - fitz is not thread-safe)
        |     - page.get_pixmap(dpi=150) -> PNG  (serial)
        |     - Gemini Vision on the 8 PNGs      (PARALLEL, ThreadPoolExecutor)
        |     - text + "[Visual & Layout Analysis]" appended
        |
        +-- DocxParser: paragraphs grouped 10-at-a-time into pseudo-pages
        +-- TextParser: whole file = page 1
        |
        v
  [4] clean_text(): collapse whitespace, strip control chars (NOT accents)
        |
        v
  [5] RecursiveCharacterTextSplitter(chunk_size=750, chunk_overlap=150)
        |
        v
  [6] chunk id = "{document_id}_p{page}_c{n}"   <-- this format matters later
      metadata  = {document_id, filename, chunk_id, upload_time, page_number, source_type}
        |
        v
  [7] EmbeddingService.get_document_embeddings()  - batches of 64
      model gemini-embedding-001, task RETRIEVAL_DOCUMENT, 768 dims
        |
        v
  [8] VectorStoreService.upsert_chunks(chunks, user_id)
      metadata["user_id"] = caller;  metadata["context"] = the chunk text
      upsert in batches of 100
        |
        v
  [9] 200 {document_id, filename, chunks_created, status:"indexed"}
      -> frontend inserts a row into Supabase `documents`
~~~

## The query path, box by box

~~~
  "What does the book say about flow?"
        |
        v
  [1] POST /api/query  ---- get_user_id_from_header() -> user_id or None (anonymous allowed)
      Pydantic: query 1..8000 chars, filters <=100, history <=100 msgs, roles restricted
        |
        v
  [2] QueryRouter.classify_query()  -> "DOCUMENT_QUERY" | "GENERAL_CHAT"
        |                                        |
        |  GENERAL_CHAT ------------------------>+---------------------+
        v                                                              |
  [3] QueryRouter.condense_query(query, history)  (only if history)    |
        |                                                              |
        v                                                              |
  [4] EmbeddingService.get_query_embedding(q, use_hyde=True)           |
        - embed the question                     (RETRIEVAL_QUERY)     |
        - Gemini writes a hypothetical answer                          |
        - embed that too                                               |
        - fuse: 0.5*query + 0.5*hyde                                   |
        |                                                              |
        v                                                              |
  [5] Pinecone query, top_k = 4*3 = 12, ALWAYS with ownership filter   |
        |                                                              |
        v                                                              |
  [6] BM25 over the 12 candidate texts -> min-max normalise            |
      combined = 0.5*cosine + 0.5*bm25_norm  -> sort -> clamp to 0..1  |
        |                                                              |
        v                                                              |
  [7] GeminiReranker: top 8 -> JSON {"ranked_ids":[...]} -> best 4     |
        |                                                              |
        v                                                              |
  [8] _expand_chunk_contexts: fetch c-1 and c+1 by id, stitch          |
        |                                                              |
        v                                                              |
  [9] ChatService._build_prompt(query, sources, history) <-------------+
        |
        v
 [10] Gemini generate_content_stream on a worker thread
        |
        v
 [11] SSE: event: metadata -> event: sources -> event: token xN -> event: complete
        |
        v
 [12] React reads the stream with fetch + ReadableStream, appends tokens,
      renders CitationsPanel from the sources event
~~~

## Every box explained

### Frontend (React 18 + TypeScript + Vite + Tailwind)

- **What it is.** A single-page application with two views (landing and dashboard) and no
  router library - view state is a `useState` in `App.tsx`.
- **Why it exists.** Users need somewhere to drop files and type questions, and streaming
  needs a client that can read a response body incrementally.
- **In.** User clicks, typed text, dropped files, the Supabase session.
- **Out.** HTTP requests to FastAPI (with a Bearer token) and direct queries to Supabase.
- **Internally.** Four hooks own all state: `useAuth` (session), `useDocuments` (library,
  upload, delete), `useChat` (sessions, messages, SSE parsing), `useAudio` (TTS playback
  and browser speech recognition).

### Authentication (Supabase + server-side JWT verification)

- **What it is.** Supabase Auth issues a signed JWT when a user signs in with email/password
  or Google OAuth. The backend verifies that JWT's signature itself.
- **Why it exists.** Without a *verified* user id, every other security control is
  decorative - you cannot scope documents to an owner you cannot prove.
- **In.** An `Authorization: Bearer <jwt>` header.
- **Out.** A user UUID (the `sub` claim), or `None` for anonymous, or an HTTP 401/503.
- **Internally.** `app/core/auth.py` reads the token's `alg` header, picks a key source
  (shared HS256 secret, or the project's JWKS for ES256/RS256), and calls `jwt.decode`
  requiring `exp` and `sub` and checking `aud == "authenticated"`.

### API layer (FastAPI routes)

- **What it is.** Four endpoints plus a health root: `POST /api/upload`,
  `DELETE /api/documents/{document_id}`, `POST /api/query`, `POST /api/tts`, `GET /`.
- **Why it exists.** To hold the secrets, enforce auth, and validate input before any
  expensive work happens.
- **Internally.** Routes are deliberately thin. They authenticate, validate with Pydantic,
  pull a pre-built service off `request.app.state`, call it, and translate exceptions into
  HTTP status codes.

> There is no `GET /api/documents`. The README used to claim one; the code has never had it. The document list is read from Supabase by the frontend. This is a real doc-vs-code discrepancy that has now been corrected in the README.

### Document processing (DocumentProcessor + parsers)

- **What it is.** Turns raw bytes into a list of clean, page-tagged text pages.
- **Why it exists.** A PDF is a rendering format, not a text format. Something has to
  extract meaning from it.
- **In.** `bytes`, a sanitised filename, a generated `document_id`.
- **Out.** `[{"id","text","metadata"}, ...]` - the chunks.
- **Internally.** Parser chosen by extension; PDFs additionally get Gemini Vision analysis.

### Chunking (RecursiveCharacterTextSplitter)

- **What it is.** Splits page text into overlapping ~750-character pieces.
- **Why it exists.** You cannot embed a whole book into one vector - meaning gets averaged
  into mush, and you could not cite a page.
- **In.** One page's cleaned text. **Out.** A list of chunk strings.
- **Internally.** Tries to split on `"\n\n"`, then `"\n"`, then `" "`, then anywhere - so
  it prefers to break at paragraph boundaries.

### Embedding (EmbeddingService)

- **What it is.** Converts text into a 768-number vector using `gemini-embedding-001`.
- **Why it exists.** Vectors are what makes *meaning-based* search possible.
- **In.** A list of strings. **Out.** A list of 768-float lists.
- **Internally.** Batches of 64; `RETRIEVAL_DOCUMENT` task type for chunks,
  `RETRIEVAL_QUERY` for questions; retries on 429 with exponential backoff; queries are
  cached in a bounded 256-entry LRU.

### Pinecone (VectorStoreService)

- **What it is.** A managed vector database - a serverless index on AWS `us-east-1`,
  768 dimensions, cosine metric.
- **Why it exists.** To find the nearest vectors to a query vector in milliseconds without
  scanning everything.
- **In.** Vectors + metadata on write; a query vector + metadata filter on read.
- **Out.** Scored matches with metadata.
- **Internally.** Every chunk's full text is stored in `metadata["context"]` so retrieval
  returns the passage itself, not just an ID.

### Query routing (QueryRouter)

- **What it is.** A zero-shot Gemini classifier at temperature 0.
- **Why it exists.** Most conversational turns do not need a vector search. Skipping it
  saves an embedding call, a HyDE call, a Pinecone read and a rerank call.
- **In.** The raw query string. **Out.** The literal string `DOCUMENT_QUERY` or `GENERAL_CHAT`.
- **Internally.** Substring match on the model's reply; anything unrecognised or any
  exception falls back to `DOCUMENT_QUERY`, because answering *with* grounding is the safer
  default.

### Retrieval + hybrid ranking + reranking + expansion

Covered in depth in Parts 9, 11, 12 and 13. In one line each: Pinecone finds 12 semantic
candidates; BM25 adds keyword sensitivity; Gemini picks the best 4; neighbours are stitched
on to restore context.

### Context construction + Gemini (ChatService)

- **What it is.** Builds the final prompt and streams the model's reply.
- **Why it exists.** This is where grounding is enforced - the instructions tell the model
  to use only the supplied context and to cite `[1]`, `[2]`.
- **In.** The query, the final sources, and the last 6 turns of history (capped at 4000
  characters). **Out.** A stream of SSE strings.

### SSE streaming

- **What it is.** `text/event-stream` - the server pushes named events down one long-lived
  HTTP response.
- **Why it exists.** So the user sees words appearing in ~1 second instead of staring at a
  spinner for 15.
- **Events.** `metadata`, `sources`, `token` (many), `complete`.

### Citations (CitationsPanel)

- **What it is.** The right-hand panel showing filename, page, relevance percentage and the
  snippet, plus clickable `[1]` chips inside the answer.
- **Why it exists.** Verifiability. It is the main reason to build RAG rather than use a
  plain chatbot.
- **Important nuance.** The *card* data is 100% real - it comes from Pinecone metadata. The
  *numbers inside the text* are written by the model and can in principle be wrong. See
  Part 16.

### TTS (edge-tts) and STT (Web Speech API)

- **TTS** runs server-side: `POST /api/tts` streams MP3 bytes from Microsoft's neural voices
  via the `edge-tts` library, with an on-disk MD5 cache.
- **STT** runs entirely in the browser using `window.SpeechRecognition` - no API key, no
  server involvement, no audio ever leaves the machine.

### CI/CD (GitHub Actions) and hosting (Render)

- **GitHub Actions** on push/PR to main: flake8, an app-import check, `pytest` (70 tests),
  then `tsc --noEmit` and a production Vite build, then optional Render deploy hooks.
- **Render** hosts two services described in `render.yaml`: a Python web service running
  `uvicorn app.main:app` with a health check on `/`, and a static site serving `dist/`
  with an SPA rewrite.
'''


PART_4 = r'''
# Part 4 - Complete Request Flow, Step by Step

This is the part to study hardest. If you can narrate these flows, you can survive almost
any question about the project.

## Flow A - User opens the application

1. Browser requests the static site from Render. Render serves `dist/index.html` and the
   bundled JS/CSS.
2. `main.tsx` mounts `<App/>` inside `React.StrictMode`.
3. `App.tsx` initialises **theme**: it reads `localStorage.darkMode`; if absent it falls back
   to the OS preference via `window.matchMedia('(prefers-color-scheme: dark)')`. An effect
   toggles the `dark` class on `<html>` and writes the choice back to localStorage.
4. `useAuth` runs: `supabase.auth.getSession()` reads any existing session from localStorage
   (no network call needed if a valid token is cached), and `onAuthStateChange` subscribes
   so later logins/logouts update state. The cleanup function unsubscribes on unmount.
5. `useDocuments(user)` runs with `user === null`, so it shows the guest library: just the
   Ikigai demo document, unless the guest previously "deleted" it (tracked in
   `localStorage.deletedDocIds`).
6. `useChat(user, activeFilters)` runs with `user === null`, so it restores guest chat
   sessions from `localStorage.guestChatSessions`, or creates a fresh welcome session.
7. `currentView` is `'landing'`, so `LandingView` renders: hero, drag-and-drop zone, feature
   cards.

> No backend call has happened yet. The FastAPI service may still be cold-starting on Render's free tier, which is why the first query can take ~50 seconds.

## Flow B - User signs up

1. User clicks **Sign In** in the header; `App` sets `isAuthModalOpen = true`.
2. `AuthModal` renders. The user toggles to "Create an Account", types email and password,
   submits.
3. `supabase.auth.signUp({email, password})` is called **from the browser directly** - the
   FastAPI backend is not involved in signup at all.
4. Two outcomes:
   - If email confirmation is disabled, Supabase returns both a `user` and a `session`. The
     modal calls `onAuthSuccess()` and closes.
   - Otherwise it returns a user but no session, and the modal shows "Check your email to
     confirm your account."
5. When a session exists, `onAuthStateChange` fires in `useAuth`, `user` becomes non-null,
   and the `useDocuments` / `useChat` effects re-run for the signed-in identity.

Google OAuth is also implemented: `supabase.auth.signInWithOAuth({provider:'google',
options:{redirectTo: window.location.origin}})` redirects to Google and back.

## Flow C - User logs in

1. `supabase.auth.signInWithPassword({email, password})`.
2. Supabase returns a session containing an **access token** (a JWT, valid ~1 hour) and a
   **refresh token**. The supabase-js client stores these in localStorage and refreshes the
   access token automatically in the background.
3. `useAuth` sets `user`. That state change triggers two effects:
   - `useDocuments`: clears `activeFilters` (they referenced the previous identity's
     filenames), then `SELECT * FROM documents WHERE user_id = <me> ORDER BY created_at DESC`,
     and appends the shared demo document to the list.
   - `useChat`: aborts any in-flight stream, then loads `chat_sessions` plus their `messages`.
     If the user has no sessions, it creates a default welcome session in Supabase.

KEY: The frontend adds `.eq('user_id', user.id)` even though RLS already enforces it. Belt and braces: RLS is the actual security boundary, the explicit filter documents intent and keeps the query correct if a policy is ever loosened.

## Flow D - User uploads a PDF (the full journey)

### D1. Browser side

1. `triggerFileSelect()` clicks the hidden `<input type="file" accept=".pdf,.docx,.txt,.md">`,
   or the user drops a file on the landing zone.
2. `uploadFile(file)` in `useDocuments` runs a client-side gate:
   - re-entrancy guard (`if (isUploading) return`)
   - extension in `['pdf','docx','txt','md','markdown']`
   - `file.size !== 0`
   - `file.size <= 25 MB`
   - **a session must exist** - if not, it shows "Sign in to upload and index documents."
3. Builds `FormData`, and POSTs to `${BACKEND_URL}/api/upload` with
   `Authorization: Bearer <access_token>`.

> These browser checks are UX, not security. The identical checks exist server-side, because anything in the browser can be bypassed with curl.

### D2. FastAPI receives it

`app/routes/document.py`:

```python
@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    user_id: str = Depends(require_user_id),   # 401 before any work happens
):
```

Then, in order:

1. `require_user_id` verifies the JWT. No token or a bad token -> **401**, and nothing is
   parsed or charged to any API.
2. `if not file.filename` -> **400**.
3. `sanitize_filename()` - takes the basename (kills `../../etc/passwd`), replaces control
   characters and `<>:"/\|?*` with `_`, strips leading dots, truncates to 200 chars.
4. Extension checked against the allow-list -> **400** if unsupported.
5. `await file.read(max_bytes + 1)` - reads at most one byte past the limit, so a 2 GB
   upload is not pulled fully into memory. Over the limit -> **413**. Empty -> **400**.
6. `document_id = str(uuid.uuid4())` - **server-generated**, never taken from the client.

### D3. Parsing (in a worker thread)

```python
chunks = await asyncio.to_thread(processor.process_file, content_bytes, filename, document_id)
```

`asyncio.to_thread` matters: parsing rasterises pages and makes blocking HTTP calls. On the
event loop it would freeze every other request.

Inside `PDFParser.parse`, for each batch of 8 pages:

1. `_render_page` runs **serially** on the calling thread: `page.get_text()` and
   `page.get_pixmap(dpi=150).tobytes("png")`.
2. `_describe_pages` runs the 8 Gemini Vision calls **in parallel** through a
   `ThreadPoolExecutor(max_workers=8)`.
3. Any returned description is appended as
   `"\n\n[Visual & Layout Analysis]:\n<text>"`.

KEY: Why serial rendering + parallel API calls? PyMuPDF `Document` objects are **not thread-safe**. The original code shared one `Document` across 8 threads, which is a real crash/corruption risk. Splitting the two phases keeps the parallelism where the latency actually is - the network - and removes the unsafe sharing.

Failure isolation: a page that throws is logged and yields empty text; the rest of the
document still indexes. A vision call that fails logs and yields `""`, so you still get the
raw text layer.

### D4. Cleaning, chunking, metadata

```python
cleaned = self.clean_text(page["text"])
if not cleaned or len(cleaned) < 10:
    continue                       # skip near-empty pages
splits = self.text_splitter.split_text(cleaned)
for split_idx, split_text in enumerate(splits):
    chunk_id = f"{document_id}_p{page['page_number']}_c{split_idx}"
```

`clean_text` collapses all whitespace runs to a single space and removes control characters
in the ranges `\x00-\x08`, `\x0b\x0c`, `\x0e-\x1f`, `\x7f`.

> Fixed bug worth mentioning in an interview: the original regex also stripped `\x7f-\xff`, which deletes every accented Latin character. German "Grüße" became "Gre". Since the TTS feature advertises German, French, Spanish, Italian and Portuguese, that was a genuine correctness bug, not a cosmetic one.

Each chunk carries: `document_id`, `filename`, `chunk_id`, `upload_time` (UTC ISO),
`page_number`, `source_type`.

### D5. Embedding and upsert

```python
embeddings = await asyncio.to_thread(self.embedding_service.get_document_embeddings, texts)
if len(embeddings) != len(chunks):
    raise RuntimeError(...)        # never silently mis-align vectors to metadata
...
meta["context"] = chunk["text"]
meta["user_id"] = user_id          # the ownership tag everything else depends on
```

Embeddings go out in batches of 64; upserts go to Pinecone in batches of 100.

### D6. Failure rollback

```python
except Exception as e:
    logger.exception(...)
    try:
        await vectorstore.delete_document(document_id, user_id=user_id)
    except Exception as cleanup_error:
        logger.error("Could not roll back partial index ...")
    raise HTTPException(status_code=502, detail="Failed to index the document...")
```

If indexing dies halfway - say batch 3 of 7 fails - the document would otherwise answer
questions with half its content and no indication anything was wrong. The rollback deletes
whatever made it in.

### D7. Response and Supabase row

`200 {document_id, filename, chunks_created, status:"indexed"}`. The frontend then inserts
a row into Supabase `documents`. If **that** insert fails, the UI says
*"Indexed, but saving to your library failed"* rather than showing a document that vanishes
on the next reload.

## Flow E - User asks a question (the full journey)

### E1. Browser

`handleSendMessage` in `useChat`:

1. Guard: empty input or already streaming -> return.
2. Capture `sessionId = activeSessionId` **now**, so tokens land in the right session even
   if the user switches tabs mid-stream.
3. Build `historyPayload` from the messages *before* appending the new one.
4. Optimistically append the user's message; persist it to Supabase.
5. Create an `AbortController`; abort any previous one.
6. `fetch(POST /api/query)` with `{query, filters, history}` and the Bearer token.

### E2. Backend entry

`get_user_id_from_header` runs as a dependency. Three outcomes:

| Header | Result |
|---|---|
| absent | `user_id = None` - anonymous, allowed, but restricted to the shared demo doc |
| present and valid | `user_id = "<uuid>"` |
| present and invalid/expired | **401** - never silently downgraded to anonymous |

Pydantic validates the body: `query` 1-8000 chars, `filters` at most 100 entries, `history`
at most 100 items each with `role` restricted to `"user"`/`"assistant"` and `text` at most
20000 chars. Bad input -> **422** before any model is called.

### E3. Routing and condensation

```python
query_type = await router_service.classify_query(query)
search_query = query
if query_type == "DOCUMENT_QUERY" and payload.history:
    search_query = await router_service.condense_query(query, payload.history)
```

Note that `query` (the original) is used for **generation**, and `search_query` (the
condensed one) is used for **retrieval**. That separation is deliberate: the condensed form
is better for search, but the original is what the user actually asked and reads better in
the prompt.

### E4. Streaming begins

The route returns a `StreamingResponse` wrapping `chat_service.stream_response(...)`, with
headers `Cache-Control: no-cache`, `Connection: keep-alive`, and crucially
`X-Accel-Buffering: no` which stops Nginx-style proxies from buffering the whole response
and destroying the streaming effect.

`request.is_disconnected` is passed in so the generator can stop early.

### E5. Inside the generator

```python
yield f"event: metadata\ndata: {json.dumps({'query_type': query_type})}\n\n"
```

Sent immediately, so the UI can show the routing badge before retrieval even starts.

If `DOCUMENT_QUERY`, retrieval runs, and the `sources` event is emitted **whether or not
retrieval succeeded** - an empty list still tells the client "this step is done".

### E6. Retrieval internals

1. **Ownership filter first**, always:
```python
{"$or": [{"user_id": {"$eq": user_id}},
         {"document_id": {"$in": SHARED_DOCUMENT_IDS}}]}
```
   Anonymous callers get `{"document_id": {"$in": SHARED_DOCUMENT_IDS}}` only.
2. **Filename filter is ANDed on**, never substituted:
```python
{"$and": [ownership_filter, {"filename": {"$in": filters}}]}
```
   So a client-supplied filter can only ever *narrow* the result set.
3. HyDE embedding, Pinecone `top_k=12`, BM25 blend, Gemini rerank to 4, neighbour expansion.

### E7. Prompt and generation

`_build_prompt` produces either a grounded prompt (with the four numbered sources and
instructions to cite them) or, if there are no sources, a general prompt that explicitly
says no document context is available and not to claim otherwise.

Generation runs on a worker thread feeding an `asyncio.Queue`; each text chunk becomes
`event: token`. Before each token the generator checks `is_disconnected()`.

### E8. Frontend reassembly

```
buffer += decoder.decode(value, {stream: true});
const packets = buffer.split('\n\n');
buffer = packets.pop() || '';        // keep the incomplete tail for next time
```

That last line is the whole trick: TCP does not respect message boundaries, so a packet can
arrive split in half. Keeping the remainder in the buffer is what makes the parser correct.

Each packet is split into `event:` and `data:` lines, the JSON is parsed, and:

- `metadata` -> set the routing badge
- `sources` -> fill the CitationsPanel
- `token` -> append to the accumulated text and update the assistant message
- `complete` -> mark `completed = true`

After the loop, if `completed` is still false the connection dropped mid-answer, so the code
throws and shows *"The response was interrupted before it finished"* rather than persisting a
truncated answer as if it were complete. A `finally` block always clears `isStreaming`.

KEY: The original code only cleared `isStreaming` inside the `complete` handler. If the stream ever ended without that event, the input box stayed disabled forever. Moving it to `finally` is a small change that fixes a total UI lock-up.

## Flow F - User deletes a document

1. `deleteDocument(id, name)` optimistically removes the card and clears the filter,
   remembering the previous list.
2. If it is the shared demo doc: no network call - it is just hidden locally via
   `localStorage.deletedDocIds`, because nobody owns it and nobody may delete it.
3. Otherwise `DELETE /api/documents/{id}` with the Bearer token.
4. Backend: `require_user_id`, then `VectorStoreService.delete_document`:
   - refuse if the id is in `SHARED_DOCUMENT_IDS` -> `PermissionError` -> **403**
   - `index.list(prefix=f"{document_id}_")` to enumerate every chunk id
   - nothing found -> `KeyError` -> **404**
   - fetch the first vector, compare `metadata["user_id"]` to the caller -> mismatch is
     `PermissionError` -> **403**
   - delete by explicit ids in batches of 500
5. Frontend checks `response.ok`; then deletes the Supabase row. If **any** step fails it
   restores the previous list, because hiding a document whose vectors are still searchable
   is worse than showing it.

## Flow G - User uses TTS

1. Click the speaker on an assistant message -> `playTTS(text)`.
2. Any in-flight request is aborted and any previous audio released (`pause`, `src=''`,
   `URL.revokeObjectURL`). Clicking the same message again toggles playback off.
3. `POST /api/tts {text, language, gender, rate}`. Pydantic enforces text 1-5000 chars,
   gender in `{female, male}`, rate 0.5-2.0.
4. `TTSService.stream_audio`: resolve the voice from `VOICE_MAP`, convert the numeric rate
   to edge-tts's `"+10%"` format, and hash `text_voice_rate` with MD5 to get a cache path.
5. **Cache hit** - stream the file in 4 KB chunks. **Cache miss** - synthesise with
   `edge_tts.Communicate`, writing to a temp file while streaming to the client, and
   `os.replace()` it into place only on success.
6. Browser turns the response into a Blob, creates an object URL, and plays it. `onended`
   and `onerror` both release the URL.

KEY: The temp-file-then-rename is not pedantry. Previously, if a user navigated away mid-synthesis, a truncated MP3 was left under a valid cache key - and every future request for that exact text/voice/rate got the broken file forever.

## Flow H - User uses speech-to-text

1. Click the mic -> `toggleSpeechToText(onTranscript)`.
2. Feature-detect `window.SpeechRecognition || window.webkitSpeechRecognition`. Missing ->
   error message (Chrome/Edge only, effectively).
3. If already listening, `stop()` and return.
4. Configure: `continuous = false`, `interimResults = false`,
   `lang = STT_LOCALE_MAP[sttLanguage]` (e.g. `ta-IN`, `de-DE`).
5. `onresult` -> `event.results[0][0].transcript` -> appended to the chat input.
   `onend` -> clear the listening state. `start()` is wrapped in try/catch so a throw does
   not strand the button in a permanent "listening" state.

This is 100% client-side. No API key, no audio upload, no server involvement.

## Flow I - User logs out

1. `handleLogout` -> `supabase.auth.signOut()` clears the stored session.
2. `onAuthStateChange` fires with `session = null`, so `user` becomes `null`.
3. The `useDocuments` effect re-runs: filters cleared, library reset to the guest view.
4. The `useChat` effect re-runs: **any in-flight stream is aborted**, streaming state is
   reset, and guest sessions are loaded from localStorage.
5. Subsequent requests carry no `Authorization` header, so the backend treats them as
   anonymous and restricts retrieval to the shared demo document.

> Session expiry mid-session: supabase-js refreshes access tokens automatically in the background. If a refresh fails and an expired token is sent, the backend returns 401 with "Session expired. Please sign in again." - it does not silently treat the request as anonymous, which would be a subtle way to leak the wrong result set.
'''
