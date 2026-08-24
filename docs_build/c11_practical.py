PART_36 = r'''
# Part 36 - Debugging Guide

Format: symptom, likely cause, where to look, how to debug, expected fix.

## Backend will not start

**Symptom:** `pydantic_core.ValidationError: 1 validation error for Settings`

- **Cause:** a required environment variable is missing. The message names the field.
- **Where:** `backend/.env` locally; the Render dashboard in production.
- **Debug:** read the field name in the error - it is exact.
- **Fix:** set the variable. The two that catch people out are `SUPABASE_JWT_SECRET` /
  `SUPABASE_URL` (at least one is required) and `CORS_ALLOW_ORIGINS`.

**Symptom:** `Value error, No way to verify Supabase access tokens.`

- **Cause:** neither Supabase verification method is configured.
- **Fix:** check Supabase -> Project Settings -> API. If you see a legacy **JWT Secret**, set
  `SUPABASE_JWT_SECRET`. If you see **JWT Keys** with an ECC/RSA key, set `SUPABASE_URL`.
  A quick way to tell: `curl https://<ref>.supabase.co/auth/v1/.well-known/jwts.json` -
  a 200 with a non-empty `keys` array means asymmetric.

**Symptom:** hangs or errors mentioning Pinecone at startup.

- **Cause:** `_ensure_index_exists()` cannot reach Pinecone, or the key is wrong.
- **Fix:** verify `PINECONE_API_KEY` and that the index region/plan is available.

## Frontend will not start or build

**Symptom:** `npm run dev` fails immediately.

- **Fix:** `npm ci` in `frontend/`. Node 20+.

**Symptom:** `tsc` errors during `npm run build`.

- **Cause:** the build runs `tsc && vite build`, so type errors block it by design.
- **Debug:** `npx tsc --noEmit` to see them without bundling.

**Symptom:** console shows *"Supabase is not configured"*.

- **Cause:** `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY` missing.
- **Important:** `VITE_*` variables are **build-time**. Changing them requires a rebuild -
  restarting the dev server is not always enough, and in production a redeploy is required.

## Gemini errors

**Symptom:** logs show `429` / `ResourceExhausted` repeatedly.

- **Cause:** free-tier per-minute quota.
- **Where:** `app/core/retry.py` logs each retry with the attempt number.
- **Fix:** wait, reduce concurrency, or raise the quota. During ingestion of a large PDF this
  is expected - the vision pass makes many calls.

**Symptom:** `404` mentioning a model name.

- **Cause:** `GEMINI_MODEL_NAME` is wrong or unavailable to your key.
- **Fix:** set it back to `gemini-2.5-flash`.

**Symptom:** answers arrive but are empty or truncated.

- **Cause:** a safety block - Gemini returns `None` for `text`.
- **Where:** the code is None-safe everywhere (`getattr(response, "text", None) or ""`), so
  this shows up as an empty answer, not a crash.

## Pinecone errors

**Symptom:** dimension mismatch.

- **Cause:** the index was created with a different dimension than 768.
- **Fix:** the index must be 768 to match `output_dimensionality`. Recreate it, or change
  both together - and re-index everything.

**Symptom:** deletes appear to work but vectors remain.

- **Cause:** the historical bug - delete by metadata filter on a serverless index.
- **Where:** `VectorStoreService.delete_document`.
- **Verify:** `for page in index.list(prefix=f"{document_id}_"): print(page.vectors)`.
- **Fix:** already fixed - deletion enumerates IDs by prefix. If you see this, you are
  running old code.

## Supabase login errors

**Symptom:** "Invalid login credentials" for a correct password.

- **Cause:** usually the email is unconfirmed.
- **Fix:** check Supabase -> Authentication -> Users, or disable email confirmation for
  development.

**Symptom:** Google OAuth redirects to a blank page or an error.

- **Cause:** the redirect URL is not in Supabase's allow-list.
- **Fix:** add your origin under Authentication -> URL Configuration.

**Symptom:** every request suddenly fails; the project seems asleep.

- **Cause:** free-tier Supabase projects pause after inactivity, and the hostname stops
  resolving.
- **Fix:** restore it in the dashboard, then wait - the auth service can return 502 for a
  minute or so while it comes back.

## Upload fails

| Status | Meaning | Fix |
|---|---|---|
| 401 | Not signed in, or bad token | Sign in; check the token is being attached |
| 400 unsupported format | Extension not in the allow-list | Use pdf, docx, txt, md |
| 400 empty | Zero-byte file | - |
| 400 no readable text | Scanned PDF and vision unavailable, or a genuinely empty document | Check `GEMINI_API_KEY` |
| 413 | Over 25 MB | Split the file or raise `MAX_UPLOAD_MB` |
| 502 | Indexing failed downstream | Check the backend log for the Gemini/Pinecone error |

## Document does not appear in the list

- **Cause 1:** the upload succeeded but the Supabase insert failed. The UI says *"Indexed,
  but saving to your library failed"*.
- **Cause 2:** RLS is blocking the insert because `user_id` does not match `auth.uid()`.
- **Debug:** browser console for the Supabase error; then query the `documents` table in the
  Supabase SQL editor.
- **Consequence:** the vectors exist and are searchable even though the document is not
  listed.

## Query returns no results

Work through in this order:

1. **Is the router sending it to retrieval?** The UI badge shows `GENERAL_CHAT` or
   `DOCUMENT_QUERY`. If it says GENERAL_CHAT, retrieval never ran.
2. **Are there any vectors for this user?**
   `index.describe_index_stats()` and a prefix list.
3. **Is a filter excluding everything?** Uncheck all document filters in the sidebar.
4. **Is the ownership filter matching?** The vectors must carry the same `user_id` as your
   token's `sub`. Documents uploaded anonymously in an older version have **no** `user_id`
   and are now unreachable by design.
5. **Did retrieval throw?** The log line is `Retrieval failed for query:`.

## Wrong or missing citations

- **Only the newest answer has clickable chips.** That is intentional - sources are stored
  per session, so older messages would link to the wrong chunks.
- **`[5]` appears as plain text.** The model cited out of range; the UI bounds-checks it.
- **Page numbers look wrong in a DOCX.** They are synthetic - groups of ten paragraphs.

## SSE does not stream (answer appears all at once)

- **Cause 1:** a proxy is buffering. The `X-Accel-Buffering: no` header exists for this; if
  you added your own reverse proxy, it needs `proxy_buffering off`.
- **Cause 2:** you are inspecting it with a tool that waits for the full body.
- **Debug:** `curl -N -X POST .../api/query -H 'Content-Type: application/json' -d '{"query":"hello"}'`
  The `-N` disables curl's own buffering; you should see events appear progressively.

## TTS does not play

- **Cause 1:** browser autoplay policy - audio needs a user gesture. It is triggered by a
  click, so this is usually fine.
- **Cause 2:** `edge-tts` failed. The stream truncates and the fetch rejects. Check the log
  for `edge-tts synthesis failed`.
- **Cause 3:** an unsupported voice/language combination - falls back to English rather than
  failing.
- **Debug:** check the Network tab - is the response `audio/mpeg` with a non-zero length?

## Deployment fails on Render

**Symptom:** build succeeds, service crashes on start with a `ValidationError`.

- **Fix:** set the missing environment variable in the dashboard.

**Symptom:** `render.yaml` settings appear to be ignored - for example the Python version
differs from the pin.

- **Cause:** the service was created manually rather than as a Blueprint, so it does not read
  the file.
- **Fix:** set everything in the dashboard, or recreate the service from the blueprint.

**Symptom:** the frontend loads but every API call fails with a CORS error.

- **Cause:** `CORS_ALLOW_ORIGINS` does not include the deployed frontend origin.
- **Fix:** set it to the exact origin, scheme included, no trailing slash.

**Symptom:** API calls go to a relative URL like `/documind-backend.onrender.com/api/query`.

- **Cause:** `VITE_BACKEND_URL` was injected as a bare host with no scheme.
- **Fix:** already handled by `normalizeBackendUrl` in `config.ts`, which prefixes `https://`.

**Symptom:** the first request after a while takes ~50 seconds.

- **Cause:** free-tier cold start. Not a bug.

## CI fails

**Symptom:** `ModuleNotFoundError: No module named 'app'` in the pytest step.

- **Cause:** the `pytest` console script does not add the working directory to `sys.path`,
  unlike `python -m pytest`.
- **Fix:** already fixed by `pythonpath = .` in `backend/pytest.ini`. Requires pytest 7.0+.

**Symptom:** flake8 fails with F401.

- **Cause:** an unused import.
- **Fix:** remove it. CI only selects E9, F63, F7 and F82 by default, so an F401 failure means
  someone widened the selection.
'''


PART_37 = r'''
# Part 37 - Demo Script (5-10 minutes)

Have the app already open and **warmed up** - hit the backend once beforehand so a free-tier
cold start does not eat the first minute of your demo.

## 0. Before you start (say this while sharing your screen)

> "I'll show you DocuMind AI. It's a full-stack RAG application - upload documents, ask
> questions about them, get answers with page-level citations. I'll walk the user flow and
> then explain what's happening behind each step."

## 1. Landing page (30 seconds)

**Do:** show the landing page, scroll the comparison section.

**Say:**
> "This is the landing page. The comparison section is the pitch: unlimited document scale
> because I only ever send the relevant chunks, real citations rather than invented ones, and
> per-user isolation. There's a drag-and-drop zone here, but uploading requires signing in -
> an indexed document needs an owner, otherwise I couldn't scope it on retrieval or deletion."

## 2. Sign in (30 seconds)

**Do:** click Sign In, log in with email/password.

**Say:**
> "Auth is Supabase - email/password and Google OAuth. Supabase issues a signed JWT that the
> browser stores. What matters is that my backend independently verifies that token's
> signature; it doesn't just trust the user id in it. An earlier version of this code
> base64-decoded the payload and trusted it, which was a complete authentication bypass -
> anyone could forge a token for any user."

## 3. The workspace (30 seconds)

**Do:** point at the three panels.

**Say:**
> "Three panels. Left is my document library and my conversations. Middle is the chat. Right
> is the citations panel, which fills in as soon as retrieval finishes - before the answer
> even starts streaming."

## 4. Upload a document (1 minute)

**Do:** upload a small PDF. Narrate while it processes.

**Say:**
> "While that's going: the backend authenticates, sanitises the filename, checks the
> extension and enforces a 25 MB cap. Then it parses. For a PDF it does two things per page -
> PyMuPDF pulls the text layer, and the page is rendered to a 150 DPI image and sent to
> Gemini Vision, which transcribes tables into Markdown and describes charts. That's the
> multimodal part: a chart with no text still becomes searchable.
>
> Pages are rendered serially and only the vision calls run in parallel, in batches of eight -
> PyMuPDF Document objects aren't thread-safe, which was a bug I had to fix.
>
> Then the text is cleaned, split into 750-character chunks with 150 overlap, embedded in
> batches of 64, and upserted to Pinecone with my user id on every vector."

## 5. Ask a document question (1.5 minutes)

**Do:** ask something answerable from the document. Let it stream.

**Say, as it happens:**
> "Watch the badge - it says DOCUMENT_QUERY. That's the agentic part: an LLM classified the
> query before anything else ran. If I'd said 'hello' it would say GENERAL_CHAT and skip
> retrieval entirely.
>
> The citations panel just filled in - that arrived on a separate SSE event before generation
> started. And now the tokens are streaming."

**Then, once it finishes:**
> "Behind that: the question was embedded, then Gemini wrote a hypothetical answer which was
> also embedded, and the two vectors were averaged - that's HyDE, and it helps because
> questions and passages are worded very differently. Pinecone returned twelve candidates,
> always with an ownership filter. I scored those with BM25 for keyword sensitivity, blended
> it fifty-fifty with cosine similarity, sent the top eight to Gemini to rerank down to four,
> and expanded each of those four with its neighbouring chunks so the model isn't reading
> half-sentences."

## 6. Show the citations (1 minute)

**Do:** point at a source card, then click an inline `[1]` chip.

**Say:**
> "Each card has the filename, the exact page, a relevance percentage and the snippet. Those
> come straight from Pinecone metadata, so the model can't invent them. Clicking a citation
> in the answer scrolls to the matching card and highlights it.
>
> One honest caveat: the numbers inside the answer text are written by the model, so it can
> mis-attribute. The cards themselves are always real. I bounds-check the numbers so an
> out-of-range citation renders as plain text instead of breaking."

## 7. Show routing with a general question (30 seconds)

**Do:** ask "what is FastAPI?"

**Say:**
> "Badge says GENERAL_CHAT, and the citations panel explains that vector lookup was bypassed.
> That saved an embedding call, a HyDE call, a Pinecone query and a rerank call. It's also
> better quality - forcing irrelevant document context into a general question makes the
> answer worse."

## 8. Document filtering (45 seconds)

**Do:** tick one document's checkbox, ask a question that only the other one answers.

**Say:**
> "Selecting documents scopes the search. Important detail: that filter is AND-ed with the
> ownership filter server-side, never substituted for it. A client-supplied filter can only
> narrow what I'm allowed to see, never widen it."

## 9. Text-to-speech (30 seconds)

**Do:** click Read Aloud. Open Voice Controls and show the language list.

**Say:**
> "Server-side TTS with edge-tts - Microsoft neural voices, ten languages plus English, with
> gender and speed controls. Audio is cached by an MD5 of the text, voice and rate, and
> written to a temp file that's atomically renamed only on success - otherwise an aborted
> request could poison a cache key with a truncated MP3 forever."

## 10. Speech-to-text (20 seconds)

**Do:** click the mic, say a short question.

**Say:**
> "That's the browser's Web Speech API - entirely client-side, no key, no audio through my
> backend. The trade-off is it's effectively Chromium-only, so I feature-detect it."

## 11. Delete a document (45 seconds)

**Do:** delete the uploaded document.

**Say:**
> "This one has the best story. Serverless Pinecone doesn't support delete-by-metadata-filter,
> but the SDK accepts the call - so deletes were silently doing nothing while the UI said
> success. Because my chunk IDs are structured as document-id, page, index, I enumerate every
> vector by ID prefix, fetch the first one to verify I actually own the document, and then
> delete by explicit IDs. If any step fails, the frontend rolls back the optimistic removal,
> because hiding a document whose vectors are still searchable is worse than showing it."

## 12. Architecture wrap-up (1 minute)

**Do:** switch to a whiteboard or just talk.

**Say:** use the Part 38 script.

## If something breaks mid-demo

Do not panic and do not pretend. Say:

> "That's the free-tier cold start - the backend spins down after inactivity and takes about
> fifty seconds to wake. Let me talk through the architecture while it comes up."

Handling a failure calmly and explaining *why* it happened often scores better than a
flawless demo.
'''


PART_38 = r'''
# Part 38 - Whiteboard Explanation

## What to draw (2-3 minutes)

Draw it in this order. Talk while you draw - do not draw in silence.

~~~
   [ BROWSER ]                                        [ SUPABASE ]
   React + TS  -------------- auth, chat history ----> Auth + Postgres + RLS
       |
       | Bearer token
       v
   [ FASTAPI ]
   routes -> services
       |
       +----> [ GEMINI ]     vision | routing | embeddings | rerank | generate
       |
       +----> [ PINECONE ]   768-dim, cosine, metadata filter on user_id
       |
       +----> [ edge-tts ]   audio


   INGEST:  file -> parse (+vision) -> chunk 750/150 -> embed -> upsert (+user_id)

   QUERY:   q -> route -> condense -> HyDE embed -> search(12) -> BM25 blend
              -> rerank(8->4) -> expand neighbours -> prompt -> SSE stream
~~~

## The exact script

**While drawing the browser box:**
> "Start with the client - React with TypeScript. It does two different things. It talks to
> Supabase directly for authentication and for reading chat history and the document list -
> that's safe because Supabase Row Level Security filters rows by the authenticated user."

**Draw the arrow to Supabase.**
> "And it talks to my FastAPI backend for anything that needs a secret key - uploading,
> querying and text-to-speech - always with a Bearer token."

**Draw the FastAPI box.**
> "FastAPI is split into routes and services. Routes are thin - authenticate, validate,
> delegate. Services hold the logic. All services are built once at startup and stored on
> app state, so I'm not rebuilding API clients per request."

**Draw the three external boxes.**
> "Three externals. Gemini does five jobs - vision parsing at upload, query routing, HyDE
> generation, reranking, and the final answer. Pinecone stores the vectors: 768 dimensions,
> cosine, and critically a metadata filter on user id, which is how tenant isolation works.
> edge-tts does the audio."

**Now draw the INGEST line.**
> "Two flows. Ingestion: the file is parsed - for PDFs that's PyMuPDF for the text layer plus
> Gemini Vision on a rendered image of each page for tables and charts. Then chunked at 750
> characters with 150 overlap, embedded in batches, and upserted to Pinecone with the owner's
> user id on every single vector."

**Now draw the QUERY line, pointing at each stage.**
> "Query: an LLM routes it - general chat skips everything to the right of here. Otherwise it
> gets condensed against history so follow-ups become standalone. Then HyDE - embed the
> question and a generated hypothetical answer, and average them. Search Pinecone for twelve
> candidates, always with the ownership filter. Score those with BM25 and blend fifty-fifty
> with cosine. Send the top eight to Gemini to rerank down to four. Expand each with its
> neighbouring chunks. Build the prompt, and stream the answer back over Server-Sent Events."

**Finish with the one-sentence summary:**
> "So: retrieval is multi-stage rather than a single lookup, and every stage that touches the
> vector store passes through a per-user filter."

## The three things to point at if they ask a follow-up

**"Where's the security?"** - Point at the arrow into FastAPI and at Pinecone.
> "Two places. The token is verified here - signature, expiry, audience - so I know who you
> are. And every Pinecone query carries an ownership filter, so you can only search your own
> vectors plus one shared demo document."

**"Where's the latency?"** - Point at the rerank stage.
> "Reranking, at four hundred milliseconds to over a second. Then HyDE generation. Pinecone
> and the fetch are under a hundred and fifty milliseconds each. If I were optimising, I'd
> replace the LLM reranker with a local cross-encoder."

**"Where would it break at scale?"** - Point at Gemini.
> "Here. Up to five calls per query and no rate limiting, so quota and cost bite long before
> Pinecone or FastAPI do."

## A simpler version if they want 60 seconds

~~~
  Upload:  document -> chunks -> vectors -> Pinecone (tagged with user id)

  Ask:     question -> [route?] -> search my vectors -> best 4 passages
                                                            |
                                          passages + question -> LLM -> streamed answer
                                                                        + citations
~~~

> "Documents get split up, turned into vectors and stored with my user id on them. When I ask
> something, an LLM decides whether it even needs the documents; if it does, we find the four
> most relevant passages, put them in the prompt, and stream back an answer that cites them."
'''


PART_39 = r'''
# Part 39 - Resume and CV Material

## One-line description

> Full-stack Agentic RAG platform (React, FastAPI, Gemini, Pinecone, Supabase) with
> multi-tenant document isolation, hybrid retrieval and streamed, cited answers.

## Two-line description

> Full-stack multi-tenant Agentic RAG platform where users upload PDFs, DOCX and Markdown and
> query them conversationally with page-level citations.
> Built on React 18, FastAPI, Gemini 2.5 Flash and Pinecone, with Supabase auth, SSE
> streaming, hybrid dense/BM25 retrieval and cross-encoder reranking, deployed on Render with
> GitHub Actions CI.

## Three resume bullets

**Version A - engineering breadth**

- Engineered a multi-tenant Agentic Multimodal RAG platform (React 18, FastAPI, Supabase,
  Pinecone) with concurrent Gemini 2.5 Flash Vision parsing of layouts, tables and charts
  alongside PyMuPDF text extraction.
- Enforced per-tenant isolation via server-side JWT signature verification (HS256 and
  JWKS-based ES256) and ownership-scoped vector filtering applied to every retrieval and
  deletion path; covered by 70 automated tests.
- Built a multi-stage retrieval pipeline - LLM intent routing, HyDE query expansion, hybrid
  dense + BM25 scoring, cross-encoder reranking and sentence-window context expansion -
  streaming grounded, cited answers over asynchronous SSE.

**Version B - depth on one thing**

- Designed and shipped a full-stack Agentic RAG system (React/TypeScript, FastAPI, Gemini,
  Pinecone, Supabase) deployed on Render with a GitHub Actions pipeline running lint, a
  70-test backend suite and a typed production build.
- Implemented multi-stage retrieval - LLM routing, HyDE fusion, hybrid dense/BM25 ranking,
  LLM cross-encoder reranking and neighbour-chunk context expansion - with a layered fallback
  so any single stage can fail without breaking the query.
- Resolved a class of silent data bugs including unverified JWT authentication, unfiltered
  anonymous vector retrieval and no-op document deletion on serverless Pinecone; added
  regression tests and a live cross-tenant isolation check.

**Version C - concise**

- Built a multi-tenant RAG platform: React 18 + FastAPI + Gemini + Pinecone + Supabase, with
  Gemini Vision document parsing and page-level citations.
- Implemented hybrid retrieval (dense + BM25), HyDE query expansion, LLM reranking and
  sentence-window context expansion behind an LLM intent router.
- Enforced tenant isolation with verified JWTs and ownership-filtered vector search; CI runs
  70 tests covering auth, isolation and the SSE contract.

## Technical skills demonstrated

| Category | Skills |
|---|---|
| Languages | Python 3.11, TypeScript, SQL |
| Backend | FastAPI, Pydantic v2, async/await, SSE, ASGI/Uvicorn |
| Frontend | React 18, hooks, Vite, Tailwind, streaming fetch |
| AI/ML | RAG architecture, embeddings, vector search, HyDE, BM25, hybrid ranking, reranking, prompt engineering |
| Data | Pinecone, PostgreSQL, Row Level Security, schema design |
| Security | JWT verification, JWKS, algorithm-confusion mitigation, multi-tenant isolation, input validation, CORS |
| Testing | pytest, fixtures, fakes/stubs, API contract testing |
| DevOps | GitHub Actions, Render, IaC via render.yaml, environment configuration |
| Practices | Layered architecture, dependency injection, graceful degradation, structured logging |

## Claims you CAN make (supported by the repository)

- 70 automated backend tests
- 5 distinct Gemini use cases in one system
- 10 languages plus English for TTS
- 4 SSE event types with a tested ordering contract
- 768-dimension embeddings, cosine, serverless Pinecone
- 750-character chunks with 150 overlap
- 12 candidates retrieved, 8 reranked, 4 used
- Two Supabase JWT signing modes supported
- Two deployed services from one blueprint

## Claims you must NOT make

- **Any percentage improvement in latency or cost.** There is no benchmark in the repository.
  A "~40% reduction" cannot be defended and will be asked about.
- "Eliminates hallucination" - it reduces it.
- "Enterprise-grade security" - there is no rate limiting or audit log.
- "Handles millions of documents" - it has never been tested at scale.
- "Real-time" - streaming is not the same as real-time.
- "OCR" without qualification - PyMuPDF reads the text layer; Gemini Vision handles the
  visual and genuinely-scanned cases.

KEY: If you want a number on your CV, measure one. The easiest defensible metric here is TTS cache-hit latency versus cold synthesis - you can time it from your own logs in five minutes. A measured small number beats an invented large one every time.
'''


PART_40 = r'''
# Part 40 - Rapid Revision Sheet

One page per concept: meaning, why it is in this project, and one question to self-test.

| Term | One-line meaning | Why we use it | Self-test question |
|---|---|---|---|
| **RAG** | Retrieve relevant text, then generate an answer from it | Lets the model answer from *your* documents and cite them | Why not just fine-tune? |
| **Agentic RAG** | An LLM decides the control flow before the pipeline runs | Skips retrieval for chit-chat; rewrites follow-ups | Is this really an agent? |
| **LLM** | Next-token predictor trained on huge text corpora | Gemini 2.5 Flash: vision, routing, HyDE, rerank, generate | Why Flash and not a bigger model? |
| **Hallucination** | Confidently stating something false | Grounding + citations + an explicit "not in the documents" escape | Can you guarantee grounding? |
| **Token** | ~3/4 of a word; the model's unit of text | Drives cost and the context limit | How many tokens is a 750-char chunk? |
| **Embedding** | A vector representing meaning | 768 dims from `gemini-embedding-001` | Why different task types for query vs document? |
| **Vector DB** | Database for nearest-neighbour search | Pinecone, serverless, cosine | Why not Postgres? |
| **Pinecone** | Managed serverless vector database | ANN + metadata filtering, which powers isolation | Why not namespaces? |
| **Cosine similarity** | Angle between vectors, ignoring length | Magnitude tracks length, not meaning | Write the formula |
| **Chunking** | Splitting documents before embedding | 750 chars / 150 overlap | What breaks if chunks are too big? |
| **Metadata** | Fields stored with each vector | user_id, filename, page, chunk_id, context | Which field enforces isolation? |
| **HyDE** | Embed a generated hypothetical answer | Bridges question/passage phrasing gap | When does HyDE hurt? |
| **BM25** | Keyword ranking: TF x IDF with length normalisation | Catches exact tokens embeddings miss | What are k1 and b? |
| **Hybrid search** | Blend dense and sparse scores | 0.5 cosine + 0.5 normalised BM25 | Why normalise first? |
| **Reranking** | Second, accurate pass over few candidates | Gemini picks the best 4 of 8 | Bi-encoder vs cross-encoder? |
| **Sentence window** | Expand a chunk with its neighbours | Precise matching, complete context | How do you find the neighbours? |
| **Gemini** | Google's LLM family | One provider for five jobs | Which model does embeddings? |
| **FastAPI** | Async Python web framework | SSE, Pydantic validation, DI | Why not Flask? |
| **Pydantic** | Validation from type hints | Request validation + fail-fast config | What status code does a validation failure produce? |
| **asyncio.to_thread** | Runs blocking code off the event loop | Every blocking SDK call uses it | What happens if you don't? |
| **SSE** | Server-to-client event stream over HTTP | 4 event types: metadata, sources, token, complete | Why not WebSockets? |
| **EventSource** | The browser's built-in SSE client | **Not used** - can't send headers or POST | So how does the frontend read the stream? |
| **React** | Component UI library | 4 hooks own all state | Why capture the session id at send time? |
| **TypeScript** | Typed JavaScript | Enforces the SSE payload contract | What runs before `vite build`? |
| **Supabase** | Hosted auth + Postgres + RLS | Auth, chat history, document list | Why can the browser query the DB directly? |
| **JWT** | Signed token carrying claims | Carries the user id in `sub` | Why verify it server-side? |
| **JWKS** | Endpoint publishing public signing keys | Supports Supabase's asymmetric mode | Why does an unreachable JWKS give 503 not 401? |
| **Authentication** | Who are you | JWT verification -> user id | Which status code on failure? |
| **Authorization** | What may you do | Ownership filter + delete check + RLS | Which status code on failure? |
| **RLS** | Postgres per-row access policies | `auth.uid() = user_id` | What does an anonymous SELECT return? |
| **Multi-tenancy** | One app, many isolated users | `user_id` metadata filter, never null | How could this fail? |
| **TTS** | Text to speech | edge-tts, 10 languages + English, MD5 cache | What's in the cache key? |
| **STT** | Speech to text | Browser Web Speech API, client-side | Which browsers? |
| **Exponential backoff** | Doubling retry delays | 2/4/8/16s for Gemini 429s | What's missing from it? |
| **CI/CD** | Automated test and deploy | Actions: flake8, import, 70 tests, tsc, build | What happens if CI fails? |
| **Render** | Cloud host | Two services from render.yaml | What's the free-tier downside? |
| **GitHub Actions** | CI runner | Runs on push/PR to main | How are secrets handled? |

## The ten numbers to memorise

| Number | What it is |
|---|---|
| **768** | Embedding dimensions / Pinecone index dimension |
| **750 / 150** | Chunk size / overlap, in characters |
| **12 / 8 / 4** | Candidates retrieved / reranked / used |
| **0.5 / 0.5** | Dense / BM25 weights in the hybrid blend |
| **1.5 / 0.75** | BM25 k1 and b |
| **64 / 100** | Embedding batch size / Pinecone upsert batch size |
| **25 MB** | Upload limit |
| **8** | Pages per vision batch (and rerank window) |
| **6 / 4000** | History turns / max history characters in the prompt |
| **70** | Backend tests |

## The five sentences that carry the most weight

1. *"Every Pinecone query passes through an ownership filter that is never null - anonymous
   users are restricted to a shared demo document, not given unfiltered access."*
2. *"Serverless Pinecone doesn't support delete-by-metadata-filter, so I enumerate vectors by
   ID prefix and verify ownership before deleting."*
3. *"The Gemini streaming iterator is blocking, so I run it on a worker thread that publishes
   into an asyncio queue - otherwise one user's answer freezes the event loop for everyone."*
4. *"It's agentic in the sense that an LLM makes a routing decision; it's not an autonomous
   agent with tools and a planning loop, and I wouldn't oversell it."*
5. *"I don't have a retrieval evaluation set, so every tuning constant is a reasonable
   default rather than a measured optimum - that's the biggest gap in the project."*
'''
