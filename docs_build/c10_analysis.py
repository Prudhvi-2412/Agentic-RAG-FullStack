PART_32 = r'''
# Part 32 - Engineering Trade-offs

Each trade-off follows the same shape: what was chosen, why, the benefit, the cost, and when
the other option wins.

## Pinecone vs PostgreSQL + pgvector

- **Chose:** Pinecone serverless.
- **Why:** managed ANN with metadata filtering, free tier, index auto-created at startup, no
  index tuning.
- **Benefit:** zero operational burden; scales without my involvement.
- **Cost:** a second data system with no transaction spanning it and Postgres. A document
  exists in both, so they can diverge. Also vendor lock-in and the serverless
  delete-by-filter limitation that cost me a real bug.
- **The other option wins when:** you already run Postgres (I do), consistency between
  vectors and metadata matters, or your corpus is small enough that pgvector's performance is
  ample. At this project's scale, pgvector is arguably the better choice.

## SSE vs WebSocket

- **Chose:** SSE.
- **Why:** the data only flows one way.
- **Benefit:** plain HTTP - Bearer auth, proxies and load balancers all work unchanged; a
  built-in event format; far less code.
- **Cost:** no client-to-server messages after the initial request, so cancelling generation
  requires a separate call or just closing the connection. No automatic reconnect in my
  implementation because I use fetch rather than EventSource.
- **The other option wins when:** you need the client to send messages mid-stream - stop
  generation, collaborative editing, live typing indicators.

## HyDE vs direct query embedding

- **Chose:** both - a 50/50 fusion.
- **Why:** HyDE bridges the question/passage style gap, but hallucinated hypotheticals can
  pull the search off-topic.
- **Benefit:** better retrieval on vague or short queries, with the raw query as an anchor.
- **Cost:** one extra generation call and one extra embedding call on every uncached query -
  roughly 0.5-1.5s of added latency before search even begins.
- **The other option wins when:** latency is critical, the query is already long and
  specific, or the corpus is a private domain the model knows nothing about.

## BM25 vs pure semantic search

- **Chose:** both - a 50/50 blend.
- **Why:** they fail in opposite directions.
- **Benefit:** exact tokens like error codes are caught by BM25; paraphrases are caught by
  embeddings.
- **Cost:** more code, an arbitrary weight I haven't tuned, and normalisation that is
  relative to the candidate set rather than absolute.
- **The other option wins when:** your corpus has no rare identifiers, or you can afford
  true sparse-dense hybrid retrieval, which is strictly better than my re-scoring approach.

## LLM reranking vs lightweight reranking

- **Chose:** Gemini as reranker.
- **Why:** zero additional infrastructure.
- **Benefit:** good intent understanding; no model to host.
- **Cost:** 400-1200ms - the slowest stage in the pipeline - plus per-query cost and
  unstructured output requiring defensive parsing.
- **The other option wins when:** latency matters. A local `ms-marco-MiniLM` cross-encoder
  runs in tens of milliseconds with no API call and no parsing risk.

## Gemini 2.5 Flash vs a larger model

- **Chose:** Flash.
- **Why:** it is the speed/cost tier, and I call it up to five times per query.
- **Benefit:** affordable enough to use for routing, HyDE and reranking as well as
  generation; fast first token.
- **Cost:** weaker reasoning on complex synthesis than a frontier model.
- **The other option wins when:** answer quality on hard multi-document reasoning matters
  more than latency and cost. A sensible hybrid: Flash for routing and reranking, a larger
  model for final generation only.

## Serverless (Render free tier) vs a persistent server

- **Chose:** Render free tier.
- **Why:** free, HTTPS included, `render.yaml` describes both services.
- **Benefit:** no infrastructure work; PR previews for the frontend.
- **Cost:** cold starts of 50+ seconds after inactivity - the most visible flaw in the live
  demo. Ephemeral disk, so the TTS cache never survives a restart.
- **The other option wins when:** you have real users. A paid instance removes cold starts
  and gives persistent disk.

## Client-side STT vs server-side STT

- **Chose:** the browser Web Speech API.
- **Why:** free, instant, no key, no audio through my backend.
- **Benefit:** zero cost and zero latency from my infrastructure.
- **Cost:** Chromium-only in practice - Firefox has no support at all. And in Chrome the
  audio does go to Google's servers, so it is not truly on-device.
- **The other option wins when:** you need cross-browser support or higher accuracy. Whisper
  via MediaRecorder would work everywhere, at the cost of bandwidth, latency and money.

## Hand-rolled Markdown renderer vs react-markdown

- **Chose:** a minimal hand-rolled renderer.
- **Why:** citation chips have to be interleaved with text nodes, which is awkward with a
  full parser.
- **Benefit:** complete control over citation rendering; no dependency.
- **Cost:** no tables, no code blocks, no links, no nested lists - despite the prompt asking
  the model for tables. This is a genuine feature gap.
- **The other option wins when:** rich formatting matters more than inline interactivity.
  `react-markdown` with a custom text renderer could do both, with more work.

## Metadata filtering vs Pinecone namespaces for isolation

- **Chose:** metadata filtering on `user_id`.
- **Why:** one index, simpler operationally, and it allows a shared demo document that
  everyone can read.
- **Benefit:** the shared-document pattern is trivial - just an `$or` clause.
- **Cost:** isolation depends on every query being written correctly. A namespace is a hard
  boundary; a filter is a soft one that a bug can bypass. Deleting all of a user's data also
  requires enumerating each document rather than dropping a namespace.
- **The other option wins when:** tenant isolation is a compliance requirement, or you need
  cheap per-tenant deletion. Namespaces make isolation structural rather than
  code-dependent.

KEY: That last trade-off is a strong one to raise unprompted. Saying "my isolation is enforced by a filter I have to get right on every query, whereas namespaces would make it structural - and I have tests specifically because it's a soft boundary" shows real security thinking.

## Optimistic UI updates vs waiting for confirmation

- **Chose:** optimistic, with rollback.
- **Why:** deleting a document should feel instant.
- **Benefit:** responsive UI.
- **Cost:** you must implement the rollback, and there is a window where the UI is lying.
- **The other option wins when:** the operation is destructive and confirmation is cheap.

## Synchronous ingestion vs a background queue

- **Chose:** synchronous, inside the upload request.
- **Why:** far simpler - no queue, no worker, no job status endpoint, no polling.
- **Benefit:** the client gets a definitive answer, and rollback on failure is
  straightforward.
- **Cost:** large documents hit request timeouts; the user waits with no progress feedback;
  a retry re-does everything.
- **The other option wins when:** documents are large. This is the single change I would make
  first if the project needed to handle real-world PDFs.
'''


PART_33 = r'''
# Part 33 - Honest Limitations

Every item is real and verifiable in the code. Volunteering these makes you more credible,
not less - and an interviewer who finds one you did not mention will trust the rest of your
answers less.

## 1. No rate limiting

- **What:** any authenticated user can issue unlimited queries and uploads.
- **Why it exists:** it was never added; the focus was correctness and isolation.
- **Why it matters:** each document query costs up to five Gemini calls. This is a direct
  route to an unexpected bill, and it is the most serious operational gap.
- **Fix:** a token bucket per user id in Redis, checked in middleware, with separate budgets
  for query and upload, returning 429 with `Retry-After`, plus a daily spend cap.

## 2. No retrieval evaluation

- **What:** there is no dataset measuring whether retrieval returns the right passages.
- **Why it exists:** building one requires manually labelling question/passage pairs.
- **Why it matters:** every tuning constant - the 50/50 weight, `top_k=12`, the rerank
  window of 8, chunk size 750 - is a reasonable default, not a measured optimum. I cannot
  prove HyDE or reranking help *on my corpus*.
- **Fix:** 50-100 labelled pairs, then measure recall@k, MRR and nDCG; add faithfulness
  scoring for generation.

## 3. Synchronous ingestion caps document size

- **What:** parsing and indexing happen inside the HTTP request.
- **Why it matters:** a 500-page PDF makes hundreds of vision calls in one request and will
  hit the platform timeout. The 25 MB cap limits the damage but does not solve it.
- **Fix:** a job queue - upload returns a job id, a worker processes batches and reports
  progress.

## 4. BM25 only re-scores dense candidates

- **What:** BM25 runs over the 12 vectors Pinecone returned, not over the corpus.
- **Why it matters:** the pipeline inherits the dense retriever's recall ceiling. A chunk
  containing a rare exact term that dense search misses is never seen.
- **Fix:** Pinecone sparse-dense vectors, or a separate sparse index fused with reciprocal
  rank fusion.

## 5. Context expansion does not cross page boundaries

- **What:** neighbours are `_p{same}_c{n±1}`, so the page never varies.
- **Why it matters:** a passage spanning the bottom of one page and the top of the next is
  never stitched.
- **Fix:** store a document-global chunk sequence alongside the page number.

## 6. Citations are per session, not per message

- **What:** `ChatSession.sources` holds only the latest retrieval.
- **Why it matters:** older assistant messages cannot have reliable clickable citations, so
  they render `[1]` as plain text.
- **Fix:** attach sources to each message and persist them with the message row.

## 7. Sources are not persisted at all

- **What:** reloading the page shows past messages with no citation cards.
- **Fix:** a `sources` JSONB column on `messages`.

## 8. Markdown rendering is minimal

- **What:** headings, bullets and whole-line bold only. No tables, code blocks, links or
  inline bold.
- **Why it matters:** the generation prompt explicitly asks for tables, and they render as
  raw pipe characters.
- **Fix:** `react-markdown` with a custom text renderer that still injects citation chips.

## 9. DOCX handling is weak

- **What:** page numbers are synthetic (groups of ten paragraphs), and table content is lost
  because `python-docx`'s `paragraphs` excludes table cells.
- **Fix:** iterate `document.element.body` to capture tables in document order.

## 10. Document filters use filenames

- **What:** the filter is `{"filename": {"$in": [...]}}`.
- **Why it matters:** two documents with the same name cannot be distinguished - selecting
  one selects both.
- **Fix:** filter on `document_id`, which is unique.

## 11. Cross-system consistency

- **What:** a document lives in Pinecone and Postgres with no transaction across them.
- **Mitigations today:** rollback on failed indexing, UI rollback on failed deletion, an
  explicit error when the library insert fails.
- **Fix:** pgvector, so one transaction covers both.

## 12. Cold starts

- **What:** Render's free tier spins down; the first request can take 50+ seconds.
- **Fix:** a paid instance, or an uptime pinger.

## 13. Caches are per-instance

- **What:** the embedding LRU is in-process; the TTS cache is on ephemeral local disk with no
  eviction.
- **Why it matters:** they do not survive restarts and do not help once scaled out.
- **Fix:** Redis for embeddings, object storage or a shared volume for audio.

## 14. Prompt injection is only mitigated by instructions

- **What:** three prompts tell the model to treat content as data.
- **Why it is survivable:** the model has no tools and no privileged actions, and isolation
  is enforced at the query level before the model runs - so injection can corrupt an answer
  but cannot cross a tenant boundary.

## 15. Parsing is not sandboxed

- **What:** PyMuPDF is C code parsing untrusted input inside the app process.
- **Fix:** run ingestion in an isolated worker with resource limits.

## 16. edge-tts is an unofficial dependency

- **What:** it speaks to an undocumented Microsoft endpoint with no key and no SLA.
- **Fix:** swap in Azure Speech or Google Cloud TTS behind the same service interface.

## 17. Speech-to-text is Chromium-only

- **What:** Firefox has no Web Speech API; Safari is unreliable.
- **Mitigation:** feature-detected with a clear message.
- **Fix:** a MediaRecorder + Whisper fallback.

## 18. No observability

- **What:** logs to stdout only. No metrics, no tracing, no error aggregation.
- **Why it matters:** I cannot tell how often retrieval returns nothing, what the route split
  is, or which stage dominates latency - which is exactly the data I would need to optimise.
- **Fix:** structured logging with per-stage timings, plus Sentry or similar.

## 19. No jitter in retry backoff

- **What:** fixed 2/4/8/16-second delays.
- **Why it matters:** under concurrency, everyone retries simultaneously - a thundering herd.
- **Fix:** multiply the delay by a random factor.

## 20. Single-region

- **What:** Pinecone in `us-east-1`, one Render region.
- **Why it matters:** latency for distant users; no failover.

KEY: If asked "what's wrong with your project?", pick three and go deep rather than listing twenty. The strongest three are: **no rate limiting** (cost risk), **no retrieval evaluation** (can't prove quality), **synchronous ingestion** (breaks on large documents).
'''


PART_34 = r'''
# Part 34 - Scalability

## 100 users

**Verdict: fine, with one caveat.**

Assume light usage - a few queries a day each, a handful of documents.

| Component | Status |
|---|---|
| FastAPI | Fine. Async, and blocking work is off the event loop |
| Pinecone | Fine. Maybe 50-100k vectors; well within serverless free limits |
| Gemini | Probably fine, but this is the caveat - free-tier quota is per-minute, so a burst of concurrent queries could hit 429s. The retry handles it at the cost of latency |
| Supabase | Fine |
| SSE connections | Fine - a handful concurrent |
| Caches | Effective, single instance |
| Render free tier | **Cold starts are the real problem** - the first user after idle waits 50+ seconds |

**Change first:** a paid Render instance to kill cold starts.

## 1,000 users

**Verdict: needs rate limiting and monitoring.**

| Component | Status |
|---|---|
| Gemini quota | **The binding constraint.** Up to 5 calls per document query - a few dozen concurrent users can exceed per-minute limits |
| FastAPI | One instance is probably still enough for query traffic; ingestion is the risk |
| Ingestion | **Problem.** Synchronous parsing occupies a request for minutes on a large PDF; several at once saturates the worker pool |
| SSE | Each stream holds a connection plus a producer thread for 5-20s; ~50 concurrent streams is a lot for one small instance |
| Pinecone | Fine. ~1M vectors is comfortable |
| Cost | **Now material.** Every query is several Gemini calls with no cap |

**Changes needed:**

1. **Rate limiting** - before anything else.
2. **Paid Render instance**, likely 2-3 replicas behind the load balancer.
3. **Redis** for shared embedding cache and rate-limit counters.
4. **Move ingestion to a queue.**
5. **Monitoring** - per-stage latency, route split, retrieval hit rate, spend per user.

## 10,000 users

**Verdict: architectural change required.**

| Component | Problem | Change |
|---|---|---|
| Gemini | Quota is the hard ceiling | Request higher limits; cache retrieval and answers; make HyDE conditional; replace the LLM reranker with a local cross-encoder to remove one call entirely |
| FastAPI | Need real horizontal scale | Autoscaling replicas; the service is stateless apart from in-process caches |
| SSE concurrency | Thousands of long-lived connections | More replicas; explicitly bound the thread pool rather than relying on the default executor |
| Ingestion | Cannot be synchronous | Dedicated worker fleet consuming a queue |
| Pinecone | ~10M+ vectors; filter-based isolation gets expensive | Move to namespaces per tenant - smaller search space *and* structural isolation |
| Postgres | Chat history grows large | Indexes on `session_id` and `user_id`; archive old sessions |
| TTS | Per-instance disk cache is useless at this scale | Object storage with a CDN in front |
| Cost | The dominant concern | Per-user quotas, aggressive caching, a cheaper routing model |

**The single most valuable change at this scale is caching retrieval results**, keyed by
`(user_id, normalised_query)` and invalidated on any upload or delete for that user. In a
system where many users ask similar questions of shared or similar documents, that removes a
large fraction of the LLM calls.

## 100,000 users

**Verdict: a different system.**

- **Self-host embeddings.** At this volume, per-call embedding pricing dominates. A hosted
  open model on your own GPUs changes the economics entirely.
- **Self-host reranking.** A small cross-encoder on GPU is orders of magnitude cheaper than
  an LLM call.
- **Tiered generation.** Cheap model by default; escalate only for hard queries.
- **Multi-region.** Regional Pinecone indexes and regional app deployments.
- **Sharding.** Per-tenant namespaces become mandatory; possibly separate indexes for large
  tenants.
- **Dedicated ingestion fleet** with autoscaling and per-tenant fairness.
- **A real evaluation and monitoring stack**, because at this size you cannot change
  retrieval by intuition.

## The bottleneck ranking

If asked "what breaks first?", answer in this order:

1. **Cost** - no rate limiting, several LLM calls per query. This bites before anything
   technical does.
2. **Gemini quota** - per-minute limits under concurrency.
3. **Synchronous ingestion** - the first thing to actually fail with an error.
4. **SSE connection and thread concurrency** per instance.
5. **Pinecone** - genuinely the least worrying; it is built for this.

KEY: Notice that the vector database - the component people assume is the bottleneck - is last. Saying "Pinecone is the part I worry about least; my constraints are LLM quota and cost" demonstrates you have actually reasoned about the system rather than reciting a generic scaling answer.
'''


PART_35 = r'''
# Part 35 - Failure Scenarios

For each: what actually happens in the current code, and whether that behaviour is safe.

## Gemini API is down

**Ingestion:** vision calls fail per page, are retried for quota errors, then logged and
skipped. The page still contributes its PyMuPDF text layer. **But** the embedding call also
fails, so `upsert_chunks` raises, the route rolls back and returns 502.

**Query:** classification fails and falls back to `DOCUMENT_QUERY`. HyDE fails and falls
back to a plain embedding - which also fails, so `similarity_search` raises. That is caught
in `stream_response`, which emits empty sources, then generation fails, producing an error
token and `complete{status:"error"}`.

**Safe?** Yes. Nothing is corrupted, no partial index is left, the user sees an error.

## Pinecone is down

**At startup:** `_ensure_index_exists` raises and the app fails to boot. Correct - it could
not serve queries anyway.

**At query time:** `similarity_search` raises, is caught, empty sources are emitted, and the
answer is generated ungrounded using the honest fallback prompt that says no document
context is available.

**At upload:** `upsert_chunks` raises; rollback is attempted (and will also fail, logged as a
cleanup error); 502 returned.

**Safe?** Yes, though degraded. The user gets an ungrounded answer clearly marked as having
no sources.

## User uploads a corrupted PDF

```python
try:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
except Exception as e:
    raise ValueError(f"The PDF could not be opened; it may be corrupted or password protected. ({e})")
```

`ValueError` becomes a **400** with a helpful message. Nothing is indexed.

**Safe?** Yes.

## User uploads a password-protected PDF

`doc.needs_pass` is checked explicitly -> `ValueError` -> **400** "Password protected PDFs
are not supported." **Safe.**

## User uploads a scanned PDF with no text layer

PyMuPDF returns empty text, but the page is still rendered and sent to Gemini Vision, which
reads the text off the image. It works.

If the Gemini client were unavailable, no chunks would be produced and the route returns
**400** "No readable text contents could be parsed from this document."

**Safe.**

## Embedding API fails mid-document

`get_document_embeddings` raises on the failing batch. `upsert_chunks` propagates. The route
catches it, calls `delete_document` to remove whatever was already upserted, and returns
502.

**Safe?** Yes - this is exactly what the rollback exists for. Without it you would have a
document answering with a third of its content.

## User loses internet during SSE

**Backend:** `request.is_disconnected()` returns true before the next token; the generator
returns; `finally` sets the stop event; the worker thread abandons the Gemini stream.

**Frontend:** the reader throws or ends without a `complete` event. Since `completed` is
false, the code throws, and the catch appends "*The response was interrupted before it
finished.*" to the partial text. The `finally` clears `isStreaming`.

**Crucially:** the partial answer is **not** persisted to Supabase, because the insert only
runs after the completion check passes.

**Safe.**

## User deletes a document while querying it

A genuine race. Three outcomes depending on timing:

1. Delete completes before the Pinecone query -> the query returns nothing from that
   document; the answer is grounded in whatever else matched.
2. Delete happens after retrieval -> the answer cites a document that no longer exists.
   Clicking the citation still shows the snippet, because it was already sent to the client.
3. Delete happens between retrieval and context expansion -> the `fetch` for neighbours
   returns nothing, the exception path logs a warning, and unexpanded chunks are used.

**Safe?** Yes in the sense that nothing crashes or leaks. Slightly confusing in case 2 - the
user sees a citation to a document they just removed. Not worth fixing; the alternative is
locking, which is far worse.

## Authentication expires mid-request

The token is verified once at the start of the request. If it expires during a 15-second
stream, that stream completes normally - the check already passed.

The *next* request sends the same expired token unless supabase-js has refreshed it. If it
has not, `ExpiredSignatureError` -> **401** "Session expired. Please sign in again."

**Safe.** Note it is *not* downgraded to anonymous, which would silently change the result
set.

## Two users upload files with the same filename

Both index normally. `document_id` is a server-generated UUID, chunk IDs are prefixed with
it, and `user_id` scopes retrieval - so there is no collision and no leakage.

**Within one user**, two same-named documents are indistinguishable in the filename filter -
selecting one selects both.

**Safe** across users; **mildly wrong** within a user. The fix is filtering by
`document_id`.

## A malicious user tries to read another user's documents

Attack surfaces and outcomes:

| Attempt | Result |
|---|---|
| Forge a JWT with another `sub` | Signature verification fails -> 401 |
| Use `alg: none` | Not in the allow-list -> 401 |
| Sign HS256 with the public JWKS key | HS256 only ever uses the shared secret -> 401 |
| Send a filename filter for someone else's file | Ownership filter is AND-ed -> zero results |
| Send no token at all | Anonymous -> restricted to shared demo documents |
| Query Supabase directly with the anon key | RLS returns zero rows |

**Safe.** Verified by unit tests and a live check against the real index.

## A malicious user tries to delete another user's document

`DELETE /api/documents/{their_id}` with a valid token: the service enumerates the prefix,
fetches the first vector, compares `metadata["user_id"]` with the caller, and raises
`PermissionError` -> **403**. Nothing is deleted.

**Safe.**

## An attacker uploads a 2 GB file

`await file.read(max_bytes + 1)` reads at most 25 MB + 1 byte, so memory is bounded, then
returns **413**. The client may still have uploaded a lot of bytes over the wire, which
consumes bandwidth and holds a connection - there is no protection against that.

**Mostly safe** - memory is protected, bandwidth is not.

## A malicious PDF contains prompt-injection text

The text is chunked, embedded and stored like any other. If retrieved, it enters the prompt.
The instruction defence may or may not hold.

**Blast radius:** the model has no tools, no function calling, no database access. The worst
case is a manipulated answer shown to the user who uploaded the file. It cannot reach
another tenant's data, because retrieval was already filtered by `user_id`.

**Acceptable**, with the caveat stated honestly.

## The reranker returns garbage

Empty text, non-JSON, a JSON array instead of an object, string ids, out-of-range ids,
duplicates - all handled. Worst case falls back to hybrid ordering.

**Safe.**

## Render restarts the container mid-request

In-flight requests are dropped. Frontend sees an interrupted stream and reports it. The TTS
cache is wiped (ephemeral disk). The embedding cache is lost. The Pinecone index and
Supabase data are unaffected.

**Safe** - all durable state is external.

## The JWKS endpoint is unreachable

```python
except jwt.PyJWKClientConnectionError as exc:
    logger.error("Could not reach the Supabase JWKS endpoint: %s", exc)
    raise HTTPException(status_code=503, detail="Authentication is temporarily unavailable.")
```

**503, not 401** - a deliberate distinction. The token may be perfectly valid; the failure is
on the server side, and telling the user to sign in again would be wrong advice.

**Safe** - and note PyJWT caches keys, so this only affects the first request or a key
rotation.

## Supabase project is paused

Free-tier Supabase projects pause after inactivity. The hostname stops resolving.

- Login fails in the browser.
- The document list and chat history fail to load (logged, empty state shown).
- **Backend auth fails with 503** if the project uses asymmetric keys, because JWKS is
  unreachable. With a shared HS256 secret, verification is local and still works.

This actually happened during development, which is how the 503 path got exercised in
practice.

**Safe** - and the 503-versus-401 choice pays off exactly here.
'''
