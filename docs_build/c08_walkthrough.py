PART_27 = r'''
# Part 27 - File-by-File Map

Only files that matter. Config files with nothing interesting in them are omitted.

## Repository root

| Path | Purpose |
|---|---|
| `README.md` | Public overview. Corrected during the audit - it previously misstated the embedding model, the hybrid weights, an endpoint that never existed, and the SSE client API. |
| `ARCHITECTURE.md` | Mermaid diagrams of the ingestion and query pipelines. Was already accurate on retrieval; updated for the ownership filter. |
| `render.yaml` | Infrastructure-as-code for both Render services. |
| `supabase_schema.sql` | The three tables plus all RLS policies. Run once in the Supabase SQL editor. |
| `smoke_test_api.py` | Manual script that hits a running server. **Not** part of the pytest suite - renamed from `test_api.py` so pytest does not try to collect it. |
| `.github/workflows/ci.yml` | The CI/CD pipeline. |
| `.gitignore` | Excludes `.env`, `node_modules`, `dist`, `__pycache__`, `backend/tts_cache/`. |

> `.gitignore` had a real bug: `!.env.example        # Allow the example template` - git does **not** support trailing comments in ignore patterns, so the comment became part of the pattern and the negation silently never matched. That is why the `.env.example` files were missing from the repo despite the README referencing them.

## Backend

| Path | Purpose |
|---|---|
| `backend/app/main.py` | Creates the FastAPI app, defines the `lifespan` that builds all services once, configures CORS, mounts routers, serves `/` as a health check. |
| `backend/app/core/config.py` | `pydantic-settings` model. Fails fast on missing critical variables; requires at least one Supabase verification method; exposes `cors_origins` and `supabase_jwks_url` as properties. |
| `backend/app/core/auth.py` | JWT verification for both signing modes, `SHARED_DOCUMENT_IDS`, and the `get_user_id_from_header` / `require_user_id` dependencies. **The security core of the project.** |
| `backend/app/core/retry.py` | `retry_with_backoff` - exponential backoff limited to Gemini 429/quota errors. |
| `backend/app/core/logging.py` | stdout logging config; quietens noisy dependency loggers. |
| `backend/app/models/chat.py` | `QueryRequest` (with length and count caps), `MessageHistoryItem` (role restricted to a `Literal`), `SourceCitation`, and the four SSE payload schemas that document the wire contract. |
| `backend/app/models/document.py` | `DocumentUploadResponse`, `DocumentMetadata`. |
| `backend/app/models/tts.py` | `TTSRequest` with a bounded rate and a `Literal` gender; max text length read from settings. |
| `backend/app/routes/document.py` | Upload and delete endpoints plus `sanitize_filename`. |
| `backend/app/routes/chat.py` | The `/api/query` SSE endpoint - routes, condenses, returns a `StreamingResponse`. |
| `backend/app/routes/tts.py` | The `/api/tts` audio streaming endpoint. |
| `backend/app/services/document.py` | `DocumentProcessor` - clean, extract, chunk, attach metadata. |
| `backend/app/services/parsers.py` | `PDFParser` (PyMuPDF + batched parallel Gemini Vision), `DocxParser`, `TextParser`. |
| `backend/app/services/embedding.py` | `EmbeddingService` - batching, task types, HyDE, bounded LRU cache. |
| `backend/app/services/vectorstore.py` | `VectorStoreService` and `calculate_bm25_scores`. Ownership filtering, hybrid scoring, prefix deletion, context expansion. **The busiest file in the project.** |
| `backend/app/services/router.py` | `QueryRouter` - classification and condensation. |
| `backend/app/services/reranker.py` | `BaseReranker` ABC and `GeminiReranker` with defensive JSON parsing. |
| `backend/app/services/chat.py` | `ChatService` - prompt construction and the threaded SSE generator. |
| `backend/app/services/tts.py` | `TTSService`, `VOICE_MAP`, atomic cache writes. |
| `backend/seed_demo_document.py` | Operator script that indexes the shared demo document. Replaces a previously public, unauthenticated, destructive `GET /api/setup-ikigai` endpoint. |
| `backend/pytest.ini` | `testpaths` and `pythonpath = .` so the suite runs under any invocation. |
| `backend/tests/*` | 70 tests. See Part 26. |
| `backend/requirements.txt` | Runtime dependencies. `langchain` and `langchain-community` were removed (only `langchain-text-splitters` is used); `pyjwt[crypto]` was added. |
| `backend/.env.example` | Template documenting every backend variable. |

## Frontend

| Path | Purpose |
|---|---|
| `frontend/src/App.tsx` | Root - view routing, dark mode, wires the four hooks to the components. |
| `frontend/src/config.ts` | `BACKEND_URL` resolution with scheme normalisation, upload limits, `DEMO_DOCUMENT_ID`. Removes what used to be triplicated URL logic. |
| `frontend/src/supabaseClient.ts` | Creates the Supabase client; logs a clear error if the env vars are missing instead of silently using a placeholder project. |
| `frontend/src/types/index.ts` | The four shared interfaces. |
| `frontend/src/hooks/useAuth.ts` | Session state and the auth-change subscription. |
| `frontend/src/hooks/useDocuments.ts` | Library load, upload with validation, delete with rollback, filename filters. |
| `frontend/src/hooks/useChat.ts` | Sessions, message persistence, the SSE reader and parser, abort handling. |
| `frontend/src/hooks/useAudio.ts` | TTS fetch and playback with object-URL lifecycle, plus Web Speech recognition. |
| `frontend/src/components/ChatPanel.tsx` | Message list, streaming display, inline citation chips, read-aloud, mic button. |
| `frontend/src/components/CitationsPanel.tsx` | The four source-panel states. |
| `frontend/src/components/Sidebar.tsx` | Conversation list and document index with filter checkboxes. |
| `frontend/src/components/AuthModal.tsx` | Email/password and Google OAuth. |
| `frontend/src/components/Header.tsx` | Nav, auth state, dark-mode toggle. |
| `frontend/src/components/LandingView.tsx` | Hero, drag-and-drop, feature comparison. |
| `frontend/src/components/VoiceController.tsx` | TTS/STT settings popover and the `LANGUAGES` list. |
| `frontend/tailwind.config.js` | Dark mode by class, Inter font, and the custom `4.5`/`5.5` spacing steps the components rely on. |
| `frontend/vite.config.ts` | Dev server port and build output. |
| `frontend/.env.example` | Template for the three `VITE_` variables. |

## Files that exist but are not part of the running system

| Path | Status |
|---|---|
| `notebooks/pdfReader.ipynb` | Exploration notebook. Not imported anywhere. |
| `source/extract_text.py`, `source/cleaning_pipeline.py` | Early standalone experiments. Not imported by the app. |
| `Ikigai ... .pdf` | The demo book, used by `seed_demo_document.py`. |

Be prepared to say "those are exploration files from before the app existed; nothing imports
them". Pretending they are part of the architecture is worse than admitting they are leftovers.
'''


PART_28 = r'''
# Part 28 - Code Walkthroughs

For each block: what it does, why it exists, who calls it, what it calls, data in, data out,
and what can fail.

## 1. FastAPI startup - `app/main.py`

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
    ...
    yield
```

- **What:** builds every service exactly once and attaches them to `app.state`.
- **Why:** SDK clients hold connection pools; per-request construction would add TLS
  handshakes to every call. It also runs `_ensure_index_exists()` once.
- **Called by:** Uvicorn, on startup.
- **Calls:** all six service constructors; `VectorStoreService.__init__` reaches Pinecone.
- **In:** validated `settings`. **Out:** a populated `app.state`.
- **Can fail:** Pinecone unreachable or a bad API key -> startup fails, which is correct -
  the app could not serve requests anyway.

## 2. Authentication - `app/core/auth.py`

```python
def _decode(token: str) -> dict:
    algorithm = jwt.get_unverified_header(token).get("alg")
    key = _signing_key_for(token, algorithm)
    return jwt.decode(
        token, key,
        algorithms=[algorithm],
        audience=settings.supabase_jwt_audience,
        options={"require": ["exp", "sub"]},
    )
```

- **What:** verifies a Supabase JWT and returns its claims.
- **Why:** it is the only thing standing between a request and someone else's documents.
- **Called by:** `get_user_id_from_header`, itself a FastAPI dependency on three endpoints.
- **Calls:** PyJWT; possibly `PyJWKClient` (network, cached).
- **In:** the raw token string. **Out:** a claims dict.
- **Can fail:** `ExpiredSignatureError` -> 401; `PyJWKClientConnectionError` -> 503;
  any other `PyJWTError` -> 401.
- **Security note:** `algorithms=[algorithm]` passes a **single** algorithm, and the key came
  from a source bound to that algorithm's family - which is what defeats algorithm confusion.

## 3. Upload route - `app/routes/document.py`

```python
max_bytes = settings.max_upload_mb * 1024 * 1024
content_bytes = await file.read(max_bytes + 1)
if len(content_bytes) > max_bytes:
    raise HTTPException(status_code=413, detail=f"File is larger than the {settings.max_upload_mb} MB upload limit.")
```

- **Why `max_bytes + 1`:** reading one byte past the limit is enough to *detect* an oversized
  file without pulling a 2 GB upload into memory.

```python
try:
    chunks = await asyncio.to_thread(processor.process_file, content_bytes, filename, document_id)
except ImportError as ie:
    raise HTTPException(500, "This file type cannot be processed on the server.")
except ValueError as ve:
    raise HTTPException(400, str(ve))
except Exception as e:
    logger.exception(...)
    raise HTTPException(500, "Failed to parse the uploaded document.")
```

- **Why three except clauses:** they map to different *causes*. `ImportError` is a server
  misconfiguration (500). `ValueError` means the file is bad (400) - and its message is safe
  to expose because the service raises deliberate, user-facing strings. Everything else is
  unknown, so it is logged and genericised.

```python
try:
    await vectorstore.upsert_chunks(chunks, user_id=user_id)
except Exception as e:
    logger.exception(...)
    try:
        await vectorstore.delete_document(document_id, user_id=user_id)
    except Exception as cleanup_error:
        logger.error("Could not roll back partial index for %s: %s", document_id, cleanup_error)
    raise HTTPException(status_code=502, detail="Failed to index the document. Please try again.")
```

- **Why the nested try:** the rollback itself can fail, and if it does that must not mask the
  original error. The user still gets a 502 about the upload, and the cleanup failure is
  logged for an operator.

## 4. Document processor - `app/services/document.py`

```python
for page in raw_pages:
    cleaned_text = self.clean_text(page["text"])
    if not cleaned_text or len(cleaned_text) < 10:
        continue
    splits = self.text_splitter.split_text(cleaned_text)
    for split_idx, split_text in enumerate(splits):
        chunk_id = f"{document_id}_p{page['page_number']}_c{split_idx}"
        chunks.append({
            "id": chunk_id,
            "text": split_text,
            "metadata": {
                "document_id": document_id,
                "filename": filename,
                "chunk_id": chunk_id,
                "upload_time": upload_time,
                "page_number": page["page_number"],
                "source_type": ext,
            },
        })
```

- **Why `< 10` is skipped:** a page containing only a page number produces a useless vector
  that adds noise to every search.
- **Why chunking is inside the page loop:** it guarantees one page number per chunk, which
  is what makes citations exact.
- **Can fail:** `extract_text` raises `ValueError` for an unsupported extension.

## 5. Embedding service - `app/services/embedding.py`

```python
for i in range(0, len(texts), _EMBED_BATCH_SIZE):
    batch = texts[i : i + _EMBED_BATCH_SIZE]
    batch_embeddings = self._embed(batch, "RETRIEVAL_DOCUMENT")
    if len(batch_embeddings) != len(batch):
        raise RuntimeError(f"Gemini returned {len(batch_embeddings)} embeddings for {len(batch)} chunks")
    embeddings.extend(batch_embeddings)
```

- **Why the count check:** vectors are matched to metadata **by list index** in
  `upsert_chunks`. A silent off-by-one would attach every chunk's text to the wrong page
  number - corrupt citations with no error anywhere. Failing loudly is far better.

## 6. Query router - `app/services/router.py`

```python
classification = (await asyncio.to_thread(self._generate, prompt)).upper()
if "DOCUMENT_QUERY" in classification:
    return "DOCUMENT_QUERY"
if "GENERAL_CHAT" in classification:
    return "GENERAL_CHAT"
logger.warning("Unexpected classifier output %r, defaulting to DOCUMENT_QUERY", classification)
return "DOCUMENT_QUERY"
```

- **Why substring rather than equality:** models add punctuation, prefixes and newlines.
  `"Classification: DOCUMENT_QUERY."` should still parse.
- **Why log the unexpected case:** silent defaults hide model drift. A warning makes it
  visible without breaking anything.

## 7. Ownership filter - `app/services/vectorstore.py`

```python
@staticmethod
def _ownership_filter(user_id: Optional[str]) -> Dict[str, Any]:
    if user_id:
        return {"$or": [
            {"user_id": {"$eq": user_id}},
            {"document_id": {"$in": SHARED_DOCUMENT_IDS}},
        ]}
    return {"document_id": {"$in": SHARED_DOCUMENT_IDS}}
```

- **Why a static method:** no instance state is needed, and it makes it trivially unit
  testable - there are tests asserting both branches by value.
- **The invariant:** it never returns `None`. There is no code path to an unfiltered query.

## 8. BM25 and hybrid blend

```python
min_bm25, max_bm25 = min(bm25_scores), max(bm25_scores)
bm25_range = max_bm25 - min_bm25
normalized_bm25 = [(s - min_bm25) / bm25_range if bm25_range > 0 else 0.0 for s in bm25_scores]

for idx, cand in enumerate(candidates):
    cand["combined_score"] = 0.5 * cand["relevance_score"] + 0.5 * normalized_bm25[idx]
candidates.sort(key=lambda x: x["combined_score"], reverse=True)
for cand in candidates:
    cand["relevance_score"] = max(0.0, min(1.0, cand.pop("combined_score")))
```

- **`if bm25_range > 0 else 0.0`** is the divide-by-zero guard for the all-equal case.
- **`cand.pop("combined_score")`** removes the temporary key so it never reaches the client -
  the SSE `sources` payload stays exactly the `SourceCitation` shape.

## 9. Reranker parsing - `app/services/reranker.py`

```python
for idx_val in ranked_ids:
    try:
        idx = int(idx_val)
    except (ValueError, TypeError):
        continue
    if 0 <= idx < len(candidates_to_rank) and idx not in seen:
        selected.append(idx)
        seen.add(idx)
```

- **What can fail and is handled:** `"two"`, `null`, `{}`, `-1`, `99`, and duplicates.
- **Why track indices instead of dicts:** comparing dict objects with `in` uses value
  equality, so two chunks with identical text would collapse into one.

## 10. Chat service - the SSE generator

```python
async def client_gone() -> bool:
    if is_disconnected is None:
        return False
    try:
        return await is_disconnected()
    except Exception:
        return False
```

- **Why wrapped in try/except:** a failure to *check* for disconnection must not abort a
  perfectly good stream. Defaulting to "still connected" is the safe direction.

```python
if query_type == "DOCUMENT_QUERY":
    try:
        sources = await self.vector_store_service.similarity_search(...)
    except Exception as ve:
        logger.exception("Retrieval failed for query: %s", ve)
        sources = []
    yield f"event: sources\ndata: {json.dumps({'sources': sources})}\n\n"
```

- **Why emit `sources` even on failure:** the frontend uses the event as a phase signal.
  Without it the citations panel would sit in its skeleton state forever.

## 11. Frontend SSE consumption - `useChat.ts`

```javascript
buffer += decoder.decode(value, { stream: true });
const packets = buffer.split('\n\n');
buffer = packets.pop() || '';
```

- **Why `{stream: true}`:** a multi-byte UTF-8 character can straddle two network chunks.
  The flag tells the decoder to buffer the incomplete sequence rather than emit a
  replacement character.
- **Why `packets.pop()`:** the final element after splitting is either an empty string (the
  buffer ended exactly on a boundary) or a partial packet. Either way it belongs back in the
  buffer.

## 12. Frontend citation rendering - `ChatPanel.tsx`

```javascript
const lastAssistantMessageId = [...messages].reverse().find(m => m.role === 'assistant')?.id;
```

- **Why `[...messages]` first:** `Array.prototype.reverse()` mutates in place. Reversing
  `messages` directly would scramble the rendered conversation order - a classic React bug.

## 13. Document deletion - the full path

```python
prefix = f"{document_id}_"
ids = await asyncio.to_thread(self._list_ids_with_prefix, prefix)
if not ids:
    raise KeyError(document_id)
owner = await asyncio.to_thread(self._owner_of, ids[:1])
if owner != user_id:
    raise PermissionError("You do not have permission to delete this document.")
for i in range(0, len(ids), _ID_BATCH_SIZE):
    await asyncio.to_thread(self.index.delete, ids=ids[i : i + _ID_BATCH_SIZE])
```

- **Order matters:** enumerate, then authorize, then delete. Authorising before enumerating
  would require a separate lookup; deleting before authorising would be catastrophic.
- **`owner != user_id` also catches `owner is None`** - an ownerless legacy vector cannot be
  deleted by anyone, which is the safe default.

```python
def _list_ids_with_prefix(self, prefix: str) -> List[str]:
    ids: List[str] = []
    for page in self.index.list(prefix=prefix):
        for vector in page.vectors or []:
            if vector.id:
                ids.append(vector.id)
    return ids
```

- **`index.list` is a generator** that follows pagination internally, so an 850-chunk
  document is enumerated across several pages transparently.
- **`if vector.id`** because `ListItem.id` is typed `str | None`.
'''
