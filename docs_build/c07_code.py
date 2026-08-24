PART_21 = r'''
# Part 21 - Frontend Architecture

## Structure

```
frontend/src/
├── App.tsx                  root: view state, theme, wires the hooks together
├── main.tsx                 React DOM entry point
├── config.ts                BACKEND_URL resolution + shared constants
├── supabaseClient.ts        Supabase client creation + config warning
├── index.css                Tailwind directives + a few custom classes
├── types/index.ts           DocumentItem, Message, SourceCitation, ChatSession
├── hooks/
│   ├── useAuth.ts           session state
│   ├── useDocuments.ts      library, upload, delete, filters
│   ├── useChat.ts           sessions, messages, SSE consumption
│   └── useAudio.ts          TTS playback + browser STT
└── components/
    ├── Header.tsx           nav, auth state, dark mode
    ├── LandingView.tsx      hero + drag-and-drop + feature cards
    ├── Sidebar.tsx          conversations + document index
    ├── ChatPanel.tsx        messages, streaming, citations, voice controls
    ├── CitationsPanel.tsx   source cards
    ├── AuthModal.tsx        sign in / sign up / Google
    └── VoiceController.tsx  TTS + STT settings popover
```

**The architectural pattern: hooks own state, components are presentational.** Every
component except `AuthModal` and `VoiceController` receives everything through props. There
is no Redux, no Context, no router library - `App.tsx` holds a `currentView` string.

For an application this size that is the right call, and it is defensible: the state is
genuinely shared by only two views, and prop drilling never exceeds one level.

## App.tsx

```javascript
const [currentView, setCurrentView] = useState<'landing' | 'dashboard'>('landing');

const [darkMode, setDarkMode] = useState<boolean>(() => {
  const saved = localStorage.getItem('darkMode');
  if (saved !== null) return saved === 'true';
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
});

useEffect(() => {
  document.documentElement.classList.toggle('dark', darkMode);
  localStorage.setItem('darkMode', String(darkMode));
}, [darkMode]);

const { user, isAuthModalOpen, setIsAuthModalOpen, handleLogout } = useAuth();
const { documents, isUploading, ..., deleteDocument } = useDocuments(user, () => setCurrentView('dashboard'));
const { chatSessions, ..., activeSession } = useChat(user, activeFilters);
```

Note the **lazy initialiser** for `darkMode` - the function form runs once instead of on
every render, and the OS-preference fallback only applies when there is no stored choice.

Note also the dependency direction: `useDocuments` owns `activeFilters` and `useChat`
*consumes* them. That is why filters chosen in the sidebar affect the query.

## useAuth

The smallest hook. Two responsibilities: expose `user`, and keep it in sync.

```javascript
useEffect(() => {
  supabase.auth.getSession().then(({ data: { session } }) => setUser(session?.user ?? null));
  const { data: { subscription } } = supabase.auth.onAuthStateChange(
    (_event, session) => setUser(session?.user ?? null)
  );
  return () => subscription.unsubscribe();
}, []);
```

The cleanup unsubscribing matters - without it, StrictMode's double-mount in development
leaves a dangling listener.

## useDocuments

**State:** `documents`, `isUploading`, `uploadStatus`, `dragActive`, `activeFilters`,
`fileInputRef`.

**The load effect:**

```javascript
useEffect(() => {
  let cancelled = false;
  setActiveFilters([]);          // filters referenced the previous identity's filenames

  if (user) {
    const loadUserDocuments = async () => {
      const { data: docs, error } = await supabase
        .from('documents').select('*')
        .eq('user_id', user.id)
        .order('created_at', { ascending: false });
      if (cancelled) return;
      if (error) { console.error(...); setDocuments([IKIGAI_DEMO_DOC]); return; }
      setDocuments([...mappedDocs, IKIGAI_DEMO_DOC]);
    };
    loadUserDocuments();
  } else { /* guest: demo doc unless locally hidden */ }

  return () => { cancelled = true; };
}, [user]);
```

Three things to point out:

- **The `cancelled` flag** prevents a race: switch identity twice quickly and the slower
  first request could otherwise overwrite the newer state.
- **`setActiveFilters([])` on identity change** - stale filenames from another account would
  silently produce zero results.
- **Supabase returns `{data, error}`; it does not throw.** So `try/catch` around it catches
  nothing. The original code used `try/catch` and silently ignored every failure. Checking
  `error` explicitly is the fix.

KEY: "supabase-js returns errors instead of throwing" is a great small detail to raise. It explains a whole class of silent failures and shows you read the library's contract rather than assuming.

**Upload gating and error surfacing:**

```javascript
const session = (await supabase.auth.getSession()).data.session;
if (!session) { failUpload('Sign in to upload and index documents.'); return; }
...
const { error: insertError } = await supabase.from('documents').insert({...});
if (insertError) {
  failUpload('Indexed, but saving to your library failed. Please retry.');
  return;
}
setDocuments(prev => [newDoc, ...prev]);
```

The row is inserted **before** the card is added to the list, so the UI never shows a
document that will vanish on refresh.

**Delete with rollback:**

```javascript
const previousDocuments = documents;
setDocuments(prev => prev.filter(doc => doc.id !== id));      // optimistic
...
if (!response.ok) throw new Error(`Vector deletion failed with status ${response.status}`);
const { error: deleteError } = await supabase.from('documents').delete().eq('id', id);
if (deleteError) throw deleteError;
...
catch (err) {
  setDocuments(previousDocuments);       // restore
}
```

Optimistic updates need a rollback path. Hiding a document whose vectors are still indexed
and still being searched is actively misleading.

## useChat

The largest and most interesting hook.

**State:** `chatSessions`, `activeSessionId`, `inputValue`, `isStreaming`,
`currentStreamText`, `retrievedSources`, `currentQueryType`, plus `chatBottomRef` and
`abortRef`.

**Session capture at send time:**

```javascript
const sessionId = activeSessionId;      // captured now, not read later
```

Every subsequent state update targets `sessionId`. If the user switches conversations
mid-stream, tokens still land in the conversation that asked the question.

**Guest persistence throttling:**

```javascript
useEffect(() => {
  if (user || isStreaming) return;
  localStorage.setItem('guestChatSessions', JSON.stringify(chatSessions));
}, [chatSessions, user, isStreaming]);
```

`chatSessions` changes on **every token**. Without the `isStreaming` guard this serialised
the entire chat history to localStorage hundreds of times per answer.

**Completion detection:**

```javascript
} else if (eventName === 'complete') {
  completed = true;
}
...
if (!completed) {
  throw new Error('The response stream ended unexpectedly.');
}
```

**Always releasing the lock:**

```javascript
} finally {
  if (abortRef.current === controller) abortRef.current = null;
  setIsStreaming(false);
  setCurrentStreamText('');
}
```

## useAudio

Covered in Parts 19 and 20. The architectural point: it is instantiated **inside
`ChatPanel`**, not in `App`, so audio state is scoped to the chat view and torn down with it.

Three refs guard against leaks: `audioRef` (the element), `audioUrlRef` (the object URL to
revoke), `requestRef` (the in-flight `AbortController`).

## Components worth knowing

### ChatPanel

The most logic-heavy component. Two rendering helpers:

- `renderMessageTextWithCitations(text, sources)` - splits on newlines and applies very
  light Markdown: `### ` headings, `- `/`* ` bullets, and `**bold**` whole lines.
- `renderInlineCitations(text, sources)` - regex-scans for `[n]` and swaps in buttons.

> Honest limitation: this is a hand-rolled mini-renderer, not a Markdown parser. It does **not** handle tables, code blocks, nested lists, links or inline bold within a sentence - even though the generation prompt asks the model for "tables where appropriate". `react-markdown` was a declared dependency that was never imported; it has been removed. If asked, say: "The renderer is deliberately minimal so I could interleave citation buttons with the text; a full Markdown parser would render tables properly but makes injecting interactive citation chips harder."

### CitationsPanel

Four mutually exclusive states, which is what makes it feel finished:

1. no query yet, or `GENERAL_CHAT` -> explainer
2. `DOCUMENT_QUERY` with sources -> the cards
3. `DOCUMENT_QUERY`, no sources, still streaming -> skeleton loaders
4. `DOCUMENT_QUERY`, no sources, finished -> "No Matching Sources" explanation

State 4 was missing originally - the panel just went blank, which looked broken.

### Sidebar

Conversations list plus the document index with checkbox filters. Filters are keyed by
**filename**, not document id, because the backend filter is
`{"filename": {"$in": [...]}}`.

> Consequence worth knowing: two documents with the same filename cannot be distinguished by the filter - selecting one selects both. Filtering by `document_id` would fix it.

### Header, AuthModal, LandingView, VoiceController

Presentational. `Header` shows the auth state and dark-mode toggle. `AuthModal` handles the
three sign-in paths with loading and error states. `LandingView` is the hero plus drag-drop.
`VoiceController` is a popover with TTS/STT tabs.

## Types

```typescript
export interface DocumentItem { id: string; name: string; chunksCount: number;
                                status: string; timestamp: string; }
export interface Message { id: string; role: 'user' | 'assistant'; text: string; }
export interface SourceCitation { filename: string; chunk_id: string;
                                  page_number: number | null;
                                  relevance_score: number; context: string; }
export interface ChatSession { id: string; title: string; messages: Message[];
                               sources: SourceCitation[]; queryType: string | null; }
```

`SourceCitation` mirrors the backend Pydantic model field-for-field - that is the
frontend/backend contract for the `sources` event.

Note `ChatSession.sources` is **per session, not per message**. That single design choice is
why old messages cannot have reliable clickable citations.

## Build configuration

`tsconfig.json` runs in strict mode with `noUnusedLocals`, `noUnusedParameters` and
`noImplicitReturns`. `npm run build` is `tsc && vite build`, so type errors fail the build.

`config.ts` handles a real deployment problem:

```javascript
function normalizeBackendUrl(raw: string): string {
  const trimmed = raw.trim().replace(/\/+$/, '');
  if (!trimmed) return '';
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return `https://${trimmed}`;
}
```

Render's `fromService` / `property: host` injects a **bare hostname** with no scheme. Without
this normalisation, `fetch("documind-backend.onrender.com/api/query")` resolves relative to
the current page and 404s.
'''


PART_22 = r'''
# Part 22 - Backend Architecture

## The four-layer structure

```
backend/app/
├── main.py              app creation, lifespan DI, CORS, router mounting
├── core/
│   ├── config.py        pydantic-settings, fail-fast validation
│   ├── auth.py          JWT verification, SHARED_DOCUMENT_IDS
│   ├── logging.py       logging setup
│   └── retry.py         exponential backoff for Gemini 429s
├── models/
│   ├── chat.py          QueryRequest, MessageHistoryItem, SourceCitation, SSE payloads
│   ├── document.py      DocumentUploadResponse, DocumentMetadata
│   └── tts.py           TTSRequest
├── routes/
│   ├── chat.py          POST /api/query
│   ├── document.py      POST /api/upload, DELETE /api/documents/{id}
│   └── tts.py           POST /api/tts
└── services/
    ├── document.py      DocumentProcessor
    ├── parsers.py       PDFParser, DocxParser, TextParser
    ├── embedding.py     EmbeddingService
    ├── vectorstore.py   VectorStoreService + calculate_bm25_scores
    ├── router.py        QueryRouter
    ├── reranker.py      BaseReranker, GeminiReranker
    ├── chat.py          ChatService
    └── tts.py           TTSService, VOICE_MAP
```

## Why routes and services are separate

**Routes handle HTTP. Services handle logic.** The concrete benefits:

1. **Testability.** Services can be tested with plain objects and no HTTP layer - which is
   exactly what most of the 70 tests do.
2. **Reusability.** `seed_demo_document.py` uses `DocumentProcessor`, `EmbeddingService` and
   `VectorStoreService` directly, with no FastAPI involved at all.
3. **Single responsibility.** A route's job is: authenticate, validate, delegate, translate
   errors into status codes. It should not know what BM25 is.
4. **Swappability.** `BaseReranker` is an ABC - `GeminiReranker` could be replaced with a
   local cross-encoder without touching a route.

A good illustration - the entire delete route:

```python
@router.delete("/documents/{document_id}")
async def delete_document_endpoint(request, document_id, user_id=Depends(require_user_id)):
    vectorstore = request.app.state.vector_store_service
    try:
        await vectorstore.delete_document(document_id, user_id=user_id)
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found in the vector index.")
    except Exception as e:
        logger.exception("Deletion failed for %s: %s", document_id, e)
        raise HTTPException(status_code=502, detail="Failed to delete the document...")
    return {"status": "success", "message": f"Document {document_id} deleted from Pinecone"}
```

The service raises **domain exceptions** (`PermissionError`, `KeyError`); the route maps them
to **HTTP semantics** (403, 404, 502). The service knows nothing about HTTP.

## Startup and dependency injection

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    model_name = settings.gemini_model_name
    embedding_svc = EmbeddingService(api_key=settings.gemini_api_key, model_name=model_name)
    reranker_svc  = GeminiReranker(api_key=settings.gemini_api_key, model_name=model_name)
    vectorstore_svc = VectorStoreService(
        api_key=settings.pinecone_api_key,
        index_name=settings.pinecone_index_name,
        embedding_service=embedding_svc,
        reranker=reranker_svc,
    )
    app.state.embedding_service = embedding_svc
    app.state.vector_store_service = vectorstore_svc
    app.state.document_processor = DocumentProcessor(api_key=..., model_name=model_name)
    app.state.query_router = QueryRouter(api_key=..., model_name=model_name)
    app.state.chat_service = ChatService(api_key=..., vector_store_service=vectorstore_svc, ...)
    app.state.reranker_service = reranker_svc
    app.state.tts_service = TTSService()
    logger.info("DocuMind AI services initialized (index=%s, model=%s)", ...)
    yield
```

**Why singletons on `app.state`?** Each service constructs an SDK client that maintains
connection pools. Rebuilding them per request would add TCP and TLS handshakes to every
call. It also means `_ensure_index_exists()` runs once, not on every upload.

> `lifespan` replaced the deprecated `@app.on_event("startup")`. Same behaviour, current API, and it gives a symmetric place for shutdown logic if it is ever needed.

## Service-by-service reference

### DocumentProcessor (`services/document.py`)

- **Responsibility:** bytes -> cleaned, chunked, metadata-tagged pieces.
- **In:** `file_bytes`, `filename`, `document_id`. **Out:** `List[{id, text, metadata}]`.
- **Depends on:** parsers, `RecursiveCharacterTextSplitter`, optionally a Gemini client.
- **Key methods:** `clean_text`, `extract_text`, `process_file`.
- **Failure modes:** `ValueError` for unsupported extension or corrupt file; `ImportError`
  if `python-docx` is missing; returns `[]` for a document with no extractable text.
- **Note:** `process_file` is **synchronous** by design - callers must wrap it in
  `asyncio.to_thread`.

### EmbeddingService (`services/embedding.py`)

- **Responsibility:** text -> 768-dim vectors; HyDE generation.
- **Key methods:** `get_query_embedding(text, use_hyde)`, `get_document_embeddings(texts)`,
  `generate_hyde_text(query)`.
- **Failure modes:** 429s retried; count mismatch raises; HyDE failures degrade silently.

### VectorStoreService (`services/vectorstore.py`)

- **Responsibility:** all Pinecone interaction plus hybrid ranking orchestration.
- **Key methods:** `upsert_chunks`, `similarity_search`, `delete_document`,
  `_ownership_filter`, `_expand_chunk_contexts`.
- **Failure modes:** `PermissionError`, `KeyError`, `ValueError` for a missing owner;
  context-expansion failures are caught and degrade.

### QueryRouter (`services/router.py`)

- **Responsibility:** classification and condensation.
- **Failure modes:** any failure returns `DOCUMENT_QUERY` / the raw query.

### GeminiReranker (`services/reranker.py`)

- **Responsibility:** reorder candidates by relevance.
- **Failure modes:** any failure returns `candidates[:top_k]`.

### ChatService (`services/chat.py`)

- **Responsibility:** prompt construction and SSE generation.
- **Depends on:** `VectorStoreService`, the Gemini client.
- **Failure modes:** emits an error token plus `complete{status:"error"}`; never raises out
  of the generator except `CancelledError`, which is re-raised deliberately.

### TTSService (`services/tts.py`)

- **Responsibility:** voice resolution, synthesis, caching.
- **Failure modes:** raises during streaming after headers are committed.

## Async discipline

The rule applied throughout: **every blocking SDK call is wrapped in `asyncio.to_thread`.**

```python
embeddings   = await asyncio.to_thread(self.embedding_service.get_document_embeddings, texts)
query_vector = await asyncio.to_thread(self.embedding_service.get_query_embedding, query, True)
response     = await asyncio.to_thread(self.index.query, vector=..., top_k=..., ...)
ids          = await asyncio.to_thread(self._list_ids_with_prefix, prefix)
chunks       = await asyncio.to_thread(processor.process_file, content_bytes, filename, document_id)
classification = await asyncio.to_thread(self._generate, prompt)
response     = await asyncio.to_thread(call_gemini)
```

KEY: This is worth stating as a principle in an interview: "An `async def` endpoint that makes a synchronous network call is worse than a plain sync endpoint, because it blocks the shared event loop instead of just its own worker thread. Every blocking call in my services goes through `asyncio.to_thread`." That is a genuinely senior observation.

## Logging

```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logging.getLogger("google").setLevel(logging.WARNING)
logging.getLogger("pinecone").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
```

Logging to **stdout** is correct for containers - Render captures stdout as the log stream.
Noisy dependencies are turned down to WARNING.

> All the original `print()` calls in services were replaced with module-level loggers. `print` has no level, no timestamp, no module name, and cannot be filtered.
'''


PART_23 = r'''
# Part 23 - Data Model

Only three systems persist anything. There is no local database, no ORM, and no file storage.

## 1. Supabase Postgres

### `documents`

```sql
CREATE TABLE public.documents (
  id           TEXT PRIMARY KEY,               -- matches the Pinecone document_id
  user_id      UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  name         TEXT NOT NULL,
  chunks_count INTEGER NOT NULL,
  status       TEXT NOT NULL,
  created_at   TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);
```

`id` is a **TEXT** column holding the same UUID string the backend generated and used as the
Pinecone `document_id`. That shared identifier is the only link between the two systems.

### `chat_sessions`

```sql
CREATE TABLE public.chat_sessions (
  id         TEXT PRIMARY KEY,                 -- e.g. "session-1755930000000"
  user_id    UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  title      TEXT NOT NULL,
  query_type TEXT,
  created_at TIMESTAMPTZ DEFAULT ... NOT NULL
);
```

Session ids are generated client-side as `session-${Date.now()}`.

### `messages`

```sql
CREATE TABLE public.messages (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id TEXT REFERENCES public.chat_sessions(id) ON DELETE CASCADE NOT NULL,
  role       TEXT NOT NULL,                    -- 'user' | 'assistant'
  text       TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT ... NOT NULL
);
```

`ON DELETE CASCADE` means deleting a session deletes its messages, and deleting an auth user
deletes everything they own.

### Relationships

~~~
  auth.users
      | 1:N                      1:N
      +---> documents      +---> chat_sessions
                           |            | 1:N
                           +------------+---> messages
~~~

**Sources are not persisted.** `ChatSession.sources` is React state only, so reloading the
page shows past messages without their citation cards.

## 2. Pinecone

One index (`documind`), default namespace, one vector per chunk. See Part 9 for the full
metadata shape. Note that **the chunk text itself lives in Pinecone metadata** - Pinecone is
both the vector index and the text store for retrieved passages.

## 3. Browser localStorage

| Key | Written by | Contents |
|---|---|---|
| `darkMode` | App.tsx | `"true"` / `"false"` |
| `guestChatSessions` | useChat | full guest chat history JSON |
| `guestActiveSessionId` | useChat | last active guest session id |
| `deletedDocIds` | useDocuments | demo doc ids a guest has hidden |
| `sb-<ref>-auth-token` | supabase-js | access + refresh tokens |

## 4. Server disk (ephemeral)

`backend/tts_cache/*.mp3`, keyed by MD5. On Render's free tier the filesystem is ephemeral,
so this cache is lost on every deploy and restart, and is not shared between instances.

## The cross-system consistency problem

This is the most interesting thing to say about the data model.

A document exists in **two** systems with no transaction spanning them:

~~~
   Pinecone: 850 vectors, document_id = X
   Postgres: 1 row,       id          = X
~~~

There are three ways they can diverge:

| Failure | Result | Handling |
|---|---|---|
| Vectors indexed, Postgres insert fails | Vectors are searchable but the doc is not listed | UI reports "Indexed, but saving to your library failed" |
| Vector delete succeeds, Postgres delete fails | Row still listed, nothing to search | Optimistic removal is rolled back so the card reappears |
| Indexing fails midway | Partial vectors | Route rolls back with `delete_document` |

KEY: Being able to say "these are two systems with no distributed transaction, here are the three divergence modes and here is what each one does" is a genuinely strong answer. The clean fix is moving vectors into Postgres with pgvector so a single transaction covers both - which is the strongest argument against Pinecone in this design.
'''


PART_24 = r'''
# Part 24 - Error Handling and Retries

## The retry helper

`app/core/retry.py`:

```python
def _is_rate_limit(exc: Exception) -> bool:
    if not isinstance(exc, APIError):
        return True                      # ResourceExhausted is always a quota error
    code = getattr(exc, "code", None)
    message = str(exc)
    return code == 429 or "ResourceExhausted" in message or "429" in message


def retry_with_backoff(func, *args, max_retries=5, initial_delay=2, backoff_factor=2, **kwargs):
    delay = initial_delay
    for attempt in range(1, max_retries + 1):
        try:
            return func(*args, **kwargs)
        except (ResourceExhausted, APIError) as e:
            if not _is_rate_limit(e):
                raise
            if attempt == max_retries:
                logger.error("Max retries (%s) reached; raising: %s", max_retries, e)
                raise
            logger.warning("Rate limited by the Gemini API. Retrying in %ss (attempt %s/%s): %s",
                           delay, attempt, max_retries, e)
            time.sleep(delay)
            delay *= backoff_factor
```

Delays: **2s, 4s, 8s, 16s** across 5 attempts - about 30 seconds of total patience.

## What is retried, and what is not

| Operation | Retried | Why |
|---|---|---|
| Gemini vision (per page) | yes | Bulk ingestion hits rate limits easily |
| Gemini query classification | yes | |
| Gemini query condensation | yes | |
| Gemini HyDE generation | yes | |
| Gemini embeddings | yes | |
| Gemini reranking | yes | |
| Gemini answer streaming | yes (on stream creation) | |
| **Pinecone operations** | **no** | The SDK has its own internal retry |
| **edge-tts synthesis** | **no** | Not wrapped |
| **Supabase (frontend)** | **no** | supabase-js handles its own |

**Only 429/quota errors are retried.** A 400 (bad request), 401 (bad key) or 404 (bad model
name) re-raises immediately - retrying a deterministic failure just wastes 30 seconds before
producing the same error.

## Why exponential backoff

If a service is rate-limiting you, retrying immediately makes it worse. Doubling the delay
gives the quota window time to reset and reduces load on a struggling service.

> Not implemented: **jitter**. With many concurrent requests, fixed delays cause a thundering herd - everyone retries at exactly 2s, then 4s. Real production code adds randomness: `delay * (0.5 + random())`. Worth volunteering as an improvement.

## The layered fallback strategy

The system is designed so that each failure degrades to something still useful:

~~~
  HyDE generation fails        -> use the raw query embedding      (slightly worse ranking)
  HyDE embedding fails         -> use the raw query embedding      (slightly worse ranking)
  Reranker fails/malformed     -> use the hybrid score order       (slightly worse ranking)
  Context expansion fails      -> use unexpanded chunks            (less context)
  Retrieval fails entirely     -> empty sources + honest prompt    (ungrounded answer)
  Classification fails         -> assume DOCUMENT_QUERY            (safe default)
  Condensation fails           -> use the raw query                (worse follow-ups)
  Generation fails             -> error token + complete{error}    (UI shows a message)
  Indexing fails midway        -> roll back partial vectors        (clean state)
~~~

KEY: This is the "graceful degradation" story and it is very strong in an interview. Say: "Every optional enhancement in the pipeline has a fallback to the version of the system without it. The reranker, HyDE and context expansion are all quality improvements - none of them can take the system down."

## HTTP status-code discipline

| Code | When |
|---|---|
| 400 | Bad file: unsupported extension, empty, corrupt, password-protected |
| 401 | Missing, malformed, expired or badly signed token |
| 403 | Valid token, but the resource belongs to someone else |
| 404 | Document not found in the index |
| 413 | Upload over 25 MB |
| 422 | Pydantic validation failure (automatic) |
| 502 | A downstream service (Gemini/Pinecone) failed |
| 503 | JWKS unreachable - authentication temporarily unavailable |

The 401-vs-403 and 502-vs-503 distinctions are deliberate and worth defending:

- **502** means "an upstream I depend on failed" - the client's request was fine.
- **503** means "I temporarily cannot verify your identity" - retry may succeed, and telling
  the user to sign in again would be wrong advice.

## Error messages never leak internals

```python
except Exception as e:
    logger.exception("Document parsing failed for %s: %s", filename, e)
    raise HTTPException(status_code=500, detail="Failed to parse the uploaded document.")
```

Detail server-side, generic message client-side. The original returned
`f"Pipeline ingestion failed: {str(e)}"`, which can expose file paths, library versions and
sometimes credential fragments.

## Interviewer questions

Q: Why retry at all?
A: Because a meaningful share of failures against LLM APIs are transient - rate limits and brief overloads. Failing the user's whole request because of a two-second quota blip is a bad trade when waiting two seconds usually succeeds.

Q: Why exponential backoff rather than a fixed delay?
A: Retrying hard against a service that's already rate-limiting makes the problem worse. Doubling the wait gives the quota window time to reset and reduces pressure. Fixed short delays would likely burn all five attempts inside a single rate-limit window and fail anyway.
FU: What's missing from your backoff?

Q: Which errors should not be retried?
A: Deterministic ones - 400 bad request, 401 bad API key, 404 unknown model. They'll fail identically every time, so retrying just adds 30 seconds of latency before the same error. My `_is_rate_limit` check re-raises anything that isn't a quota error immediately.

Q: What happens after retries are exhausted?
A: The exception propagates to the caller, and what happens next depends on how important the operation was. If it was HyDE or reranking, there's a fallback and the user never notices. If it was the primary generation call, the SSE stream emits a generic error token and `complete` with status error. If it was indexing, the upload rolls back and returns 502.

Q: How do you avoid leaking internals in errors?
A: Every route logs the full exception server-side with `logger.exception` and returns a fixed, generic message. The streaming path does the same - it yields a fixed apology string rather than `str(e)`, which previously put raw exception text straight into the user's chat transcript.
'''


PART_25 = r'''
# Part 25 - Caching

There are exactly **three** caches. No Redis, no Memcached, no CDN caching layer of my own.

## 1. Query embedding cache (in-process, bounded LRU)

| Property | Value |
|---|---|
| Location | `EmbeddingService.query_cache`, an `OrderedDict` |
| Key | `f"hyde_{text}"` or `f"raw_{text}"` |
| Value | `List[float]` of 768 floats |
| Max size | 256 entries |
| Eviction | LRU - `popitem(last=False)` |
| Lifetime | Process lifetime; lost on restart |
| Scope | One server instance |

```python
def _cache_put(self, key: str, value: List[float]) -> None:
    self.query_cache[key] = value
    self.query_cache.move_to_end(key)
    while len(self.query_cache) > _QUERY_CACHE_MAX:
        self.query_cache.popitem(last=False)
```

**Why:** a cached HyDE query avoids two embedding calls **and** one Gemini generation call -
the single most expensive part of a repeated query.

**Memory:** 256 entries x 768 floats x ~8 bytes plus Python object overhead is roughly
1.5-4 MB. Bounded and negligible.

**Risks:** none for correctness - embeddings for identical text are deterministic. The key
is the full query text, so there is no collision risk.

> Originally a plain unbounded `dict`. A long-running server with varied traffic would grow it forever - a slow memory leak.

## 2. TTS audio cache (on disk)

| Property | Value |
|---|---|
| Location | `backend/tts_cache/<md5>.mp3` |
| Key | `MD5(text + "_" + voice + "_" + rate)` |
| Max size | **unbounded** |
| Eviction | **none** |
| Lifetime | Until the container restarts (ephemeral disk on Render) |
| Scope | One instance |

**Why:** synthesis is seconds of latency against an external service; a hit is a local read.

**Risks and gaps, stated honestly:**

- **No eviction.** The directory grows without limit. On Render's ephemeral disk this is
  self-limiting by accident, not by design.
- **Not shared** across instances - each replica builds its own.
- **Cache poisoning by truncation** was possible before the temp-file fix.
- MD5 collisions are theoretically possible; consequence would be serving wrong audio.

> These MP3s were originally **committed to git**. They are now untracked and gitignored - generated artefacts do not belong in version control.

## 3. Pinecone JWKS cache (inside PyJWT)

```python
_jwk_client = jwt.PyJWKClient(settings.supabase_jwks_url, cache_keys=True)
```

`PyJWKClient` caches fetched signing keys in memory, so the JWKS endpoint is not hit on every
request - only on the first, and again if an unknown `kid` appears (i.e. after key rotation).
The client is itself a lazily-created singleton guarded by a lock:

```python
_jwk_client = None
_jwk_client_lock = threading.Lock()

def _get_jwk_client():
    global _jwk_client
    if _jwk_client is None:
        with _jwk_client_lock:
            if _jwk_client is None:
                _jwk_client = jwt.PyJWKClient(settings.supabase_jwks_url, cache_keys=True)
    return _jwk_client
```

That is the double-checked locking pattern - avoid taking the lock on the common path, but
re-check inside it so two concurrent first-requests cannot both construct a client.

## Browser-side caching

- `Cache-Control: max-age=86400` on the TTS response, so the browser will not re-request
  identical audio for a day.
- `Cache-Control: no-cache` on the SSE response - streaming must never be cached.
- localStorage is persistence, not caching.

## What is NOT cached, and why it matters

| Not cached | Consequence |
|---|---|
| Retrieval results | The same question re-runs the full pipeline, including reranking |
| Generated answers | Identical questions cost full generation every time |
| Document embeddings | Correct - each chunk is embedded exactly once |
| Supabase queries | Every page load re-queries documents and sessions |

**The biggest missed opportunity is a retrieval/answer cache.** In a demo where the same
handful of questions get asked repeatedly, caching `(user_id, query)` -> sources would remove
almost all cost. The reason not to do it naively: results must be invalidated whenever the
user uploads or deletes a document, and the cache key must include `user_id` or you leak
across tenants.

KEY: If asked "what would you cache next?", the answer is: "Retrieval results keyed by user id plus the normalised query, invalidated on any upload or delete for that user. The user id must be in the key - a cache keyed only on the query text would be a cross-tenant data leak."

## Interviewer questions

Q: What do you cache and why?
A: Three things. Query embeddings in a bounded 256-entry LRU, because a repeated question otherwise costs two embedding calls plus a HyDE generation. TTS audio on disk keyed by MD5 of text, voice and rate, because synthesis is slow and external. And JWKS signing keys inside PyJWT, so I'm not fetching public keys on every request.

Q: Why bound the embedding cache?
A: Because an unbounded dict on a long-running server is a memory leak. It was originally a plain dict; making it an OrderedDict with LRU eviction at 256 entries caps it at a few megabytes.

Q: What are the risks of your TTS cache?
A: Unbounded growth with no eviction - it happens to be safe only because Render's disk is ephemeral, which is luck rather than design. It's also per-instance, so it doesn't help once you scale out. And before I fixed it, an aborted request could leave a truncated MP3 under a valid key and poison that entry permanently; now I write to a temp file and atomically rename only on success.

Q: Would you add Redis?
A: Only when scaling past one instance. Right now both caches are in-process or on local disk, which is fine for a single container. With multiple replicas they'd be duplicated and mostly cold. Redis would give a shared embedding cache, a shared TTS cache and a place for rate-limit counters - which is the feature I'm actually missing most.
'''


PART_26 = r'''
# Part 26 - CI/CD and Deployment

## The pipeline

~~~
  git push / pull request to main
            |
            v
   GitHub Actions (.github/workflows/ci.yml)
            |
     +------+-------------------------+
     |                                |
  backend-ci                     frontend-ci
  - setup Python 3.11            - setup Node 20
  - pip install -r requirements  - npm ci
  - flake8 app/ tests/           - npx tsc --noEmit
  - import app.main              - npm run build
  - pytest tests/ (70 tests)     - upload dist/ artifact
     |                                |
     +------+-------------------------+
            |  (both must pass, only on main)
            v
      deploy-notify
      - POST RENDER_BACKEND_DEPLOY_HOOK
      - POST RENDER_FRONTEND_DEPLOY_HOOK
            |
            v
        Render builds and deploys both services
~~~

## The backend job

```yaml
- name: Lint with flake8
  run: |
    pip install flake8
    flake8 app/ tests/ --count --select=E9,F63,F7,F82 --show-source --statistics
```

Those specific codes are chosen deliberately: **E9** syntax errors, **F63** comparison bugs,
**F7** misplaced statements, **F82** undefined names. These are *bugs*, not style. Style
warnings would create noise without catching defects.

```yaml
- name: Verify FastAPI app imports correctly
  env:
    GEMINI_API_KEY: placeholder
    PINECONE_API_KEY: placeholder
    SUPABASE_JWT_SECRET: placeholder-jwt-secret-for-ci-only
    CORS_ALLOW_ORIGINS: http://localhost:5173
  run: python -c "from app.main import app; print('...')"
```

This catches import errors, circular imports and syntax problems without any network access.
It works because the lifespan handler - which does build real clients - only runs when the
app actually starts serving, not on import.

```yaml
- name: Run backend tests
  run: |
    pip install "pytest>=7.0"
    pytest tests/ -q
```

## The pytest.ini that makes CI work

```ini
[pytest]
testpaths = tests
pythonpath = .
```

This exists because of a genuine CI failure. Running `python -m pytest` adds the current
directory to `sys.path`; running the `pytest` console script **does not**. So the suite
passed locally and failed in CI with `ModuleNotFoundError: No module named 'app'`. Setting
`pythonpath = .` in `pytest.ini` makes it work under any invocation, which is the root-cause
fix rather than changing the CI command.

KEY: This is a good "debugging" story: the same tests, the same code, one passes and one fails, and the difference is how the test runner was invoked. `pythonpath` requires pytest 7.0+, so CI pins `pytest>=7.0`.

## What the 70 tests actually cover

| File | Focus |
|---|---|
| `test_auth.py` | Valid tokens, forged signatures, `alg: none`, expiry, wrong audience, malformed headers, anonymous |
| `test_auth_asymmetric.py` | ES256 via JWKS, wrong-key rejection, JWKS outage -> 503, algorithm-confusion defence, config permutations |
| `test_vectorstore.py` | Ownership filter shapes, delete authorization, BM25 correctness and edge cases |
| `test_retrieval_pipeline.py` | Filter always sent, anonymous scoping, filters cannot widen, candidate pool size, HyDE enabled, score clamping |
| `test_documents.py` | Filename sanitisation, accent preservation, chunk ID schema, empty docs, request validation, TTS voice mapping |
| `test_api_contract.py` | Auth enforcement per endpoint, size/extension rejection, and the exact SSE event ordering |

The suite runs with **no network access** - Pinecone and Gemini are replaced with fakes, and
`conftest.py` sets placeholder environment variables before any app import.

## render.yaml

```yaml
services:
  - type: web
    name: documind-backend
    runtime: python
    rootDir: backend
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    plan: free
    healthCheckPath: /
    envVars:
      - key: GEMINI_API_KEY
        sync: false
      - key: PINECONE_API_KEY
        sync: false
      - key: SUPABASE_JWT_SECRET
        sync: false
      - key: SUPABASE_URL
        sync: false
      - key: CORS_ALLOW_ORIGINS
        sync: false
      - key: PINECONE_INDEX_NAME
        value: documind
      - key: GEMINI_MODEL_NAME
        value: gemini-2.5-flash
      - key: PYTHON_VERSION
        value: "3.11"

  - type: web
    name: documind-frontend
    runtime: static
    rootDir: frontend
    buildCommand: npm install && npm run build
    staticPublishPath: dist
    pullRequestPreviewsEnabled: true
    envVars:
      - key: VITE_SUPABASE_URL
        sync: false
      - key: VITE_SUPABASE_ANON_KEY
        sync: false
      - key: VITE_BACKEND_URL
        fromService:
          name: documind-backend
          type: web
          property: host
    routes:
      - type: rewrite
        source: /*
        destination: /index.html
```

Points worth explaining:

- **`sync: false`** means "do not read this from the file - I will set it in the dashboard".
  That is how secrets stay out of the repository.
- **`$PORT`** is injected by Render; binding a hard-coded port would fail.
- **`healthCheckPath: /`** - the root endpoint returns a small JSON status object.
- **The SPA rewrite** sends every path to `index.html` so client-side view state survives a
  direct URL hit or refresh.
- **`property: host`** injects a **bare hostname with no scheme** - which is exactly why
  `config.ts` prefixes `https://`.

> **Important operational note.** A Render service created manually rather than from the blueprint does **not** read `render.yaml`. Evidence from a real deploy log: it ran Python 3.14 despite the file pinning 3.11, and `SUPABASE_JWT_SECRET` was unset. In that situation every variable must be set in the dashboard.

## Build-time vs runtime environment variables

A distinction that trips people up:

- **Frontend (`VITE_*`)** are **build-time**. Vite substitutes them into the bundle during
  `npm run build`. Changing one requires a **rebuild** - restarting does nothing. And because
  they end up in the bundle, they are **public**. That is fine for the Supabase URL and anon
  key, which are designed to be public and protected by RLS. It is why the Gemini and
  Pinecone keys are backend-only.
- **Backend** variables are **runtime** - read by `pydantic-settings` at process start, so a
  restart is enough.

## Cold starts

Render's free tier spins a service down after inactivity. The first request can take
**50+ seconds**. This is visible in the deploy dashboard as a warning and is the single most
noticeable UX problem in the deployed demo. Mitigations: a paid instance, or an external
uptime pinger.

## Interviewer questions

Q: Why Render?
A: It deploys both a Python web service and a static site from one `render.yaml`, has a free tier, gives HTTPS and health checks out of the box, and can inject one service's host into another's environment. Compared to running my own VM it's far less work; compared to Vercel plus a separate backend host it keeps everything in one place.
FU: What's the downside of the free tier?

Q: What does your CI actually verify?
A: For the backend: flake8 for real bug classes, an app-import check with placeholder env vars, and 70 pytest tests covering JWT rejection cases, tenant isolation, deletion authorization, BM25 edge cases, filename sanitisation and the exact SSE event ordering. For the frontend: a strict TypeScript check and a production build. The tests need no network - Pinecone and Gemini are faked.

Q: What happens after you push to main?
A: Both CI jobs run in parallel. If either fails, the deploy job is skipped because it declares `needs: [backend-ci, frontend-ci]`. If both pass and the ref is main, it POSTs to the Render deploy hooks, which trigger builds. The hook step is written to skip gracefully if the secret isn't configured rather than failing the run.

Q: How are secrets handled?
A: They're never in the repo. `render.yaml` marks them `sync: false`, so the values live in the Render dashboard. CI uses obvious placeholder values for the import and test steps, and real secrets only as GitHub Actions secrets for the frontend build. `.env` files are gitignored, with `.env.example` templates committed.
FU: Your frontend env vars end up in the bundle - isn't that a leak?

Q: Was there anything wrong with your CI?
A: Yes, and it was a good lesson. The suite passed locally with `python -m pytest` but failed in CI with `ModuleNotFoundError: No module named 'app'`, because the `pytest` console script doesn't put the working directory on `sys.path` while `python -m pytest` does. I fixed it at the root by adding `pythonpath = .` to `pytest.ini`, so it works under any invocation, rather than just changing the CI command to paper over it.
'''
