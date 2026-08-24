PART_29 = r'''
# Part 29 - Interview Question Bank

Three levels. Answers are deliberately short here - the long-form versions live in the
topic chapters and in Part 41.

## Level 1 - Beginner (50 questions)

Q: What is RAG?
A: Retrieval-Augmented Generation. You search a knowledge store for relevant passages, paste them into the prompt, and let the model answer from them instead of from memory.

Q: What problem does RAG solve?
A: Language models can only answer from training data, hallucinate when unsure, and can't cite. RAG gives them your current, private documents and makes answers verifiable.

Q: What is an embedding?
A: A list of numbers - 768 in this project - representing the meaning of text, arranged so similar meanings produce similar vectors.

Q: What is a vector?
A: Just a list of numbers. An embedding is a vector.

Q: What is a vector database?
A: A database optimised for "find the stored vectors most similar to this one", using approximate nearest-neighbour indexes rather than B-trees.

Q: What is Pinecone?
A: A managed serverless vector database. Mine is a 768-dimension, cosine-metric index called `documind` on AWS us-east-1.

Q: What is cosine similarity?
A: The cosine of the angle between two vectors - dot product over the product of magnitudes. 1 means same direction, 0 unrelated, -1 opposite. It ignores length.

Q: What is an LLM?
A: A model that predicts the next token repeatedly to produce text, trained on very large text corpora.

Q: What is Gemini?
A: Google's LLM family. I use `gemini-2.5-flash` for vision, routing, HyDE, reranking and generation, and `gemini-embedding-001` for embeddings.

Q: What is a token?
A: The unit a model reads - roughly three-quarters of a word. Billing and context limits are measured in tokens.

Q: What is a prompt?
A: The complete text sent to the model: instructions, retrieved context, history and the question.

Q: What is a context window?
A: The maximum number of tokens a model can consider at once. Its finiteness is why RAG exists.

Q: What is hallucination?
A: When a model states something false confidently, because it optimises for plausible text rather than truth.

Q: What is FastAPI?
A: A modern async Python web framework with automatic validation from type hints and OpenAPI docs. I use it for the backend.

Q: Why FastAPI and not Flask?
A: Native async, which I need for SSE streaming and concurrent I/O, plus Pydantic validation built in.

Q: What is React?
A: A JavaScript library for building UIs from components with declarative state. The frontend is React 18 with TypeScript.

Q: What is TypeScript?
A: JavaScript with static types. It catches contract mismatches at build time - my build runs `tsc` before bundling.

Q: What is Vite?
A: The frontend build tool and dev server. Fast dev via native ES modules, Rollup for production builds.

Q: What is Tailwind CSS?
A: A utility-first CSS framework - you compose styles from small classes in the markup rather than writing separate CSS.

Q: What is Supabase?
A: A hosted backend platform. I use its Auth, its Postgres database, and its Row Level Security.

Q: What is SSE?
A: Server-Sent Events - a one-directional stream of named events from server to client over plain HTTP, content type `text/event-stream`.

Q: What is a JWT?
A: A JSON Web Token - base64url header, payload and signature. The payload carries claims like the user id; the signature proves it was issued by someone holding the key.

Q: What does the `sub` claim mean?
A: Subject - the user's unique id. In Supabase it's the user's UUID.

Q: What is chunking?
A: Splitting a document into small pieces before embedding, so each vector represents one idea and citations can point at a page.

Q: What chunk size do you use?
A: 750 characters with 150 characters of overlap.

Q: What is metadata in a vector database?
A: Extra fields stored with each vector - here filename, page number, chunk id, user id and the chunk text - usable for filtering and display.

Q: What is semantic search?
A: Searching by meaning rather than exact characters, so "how to live longer" matches "longevity".

Q: What is BM25?
A: A keyword ranking function using term frequency, inverse document frequency and length normalisation.

Q: What is reranking?
A: A second, more accurate scoring pass over a small candidate set from a cheap first-stage retrieval.

Q: What is HyDE?
A: Hypothetical Document Embeddings - generate a fake answer to the query, embed that, and search with it because it looks more like the passages you're searching.

Q: What is PyMuPDF?
A: The `fitz` library. I use it to extract text from PDF pages and render pages to PNG images.

Q: What is edge-tts?
A: A Python library that uses Microsoft Edge's neural text-to-speech voices. No API key required.

Q: What is the Web Speech API?
A: A browser API for speech recognition. My speech-to-text runs entirely client-side through it.

Q: What is CORS?
A: Cross-Origin Resource Sharing - the browser rule that a page on one origin can't call another origin unless that server allows it. I configure an explicit allow-list.

Q: What is an API key?
A: A secret string identifying your account to a service. Mine for Gemini and Pinecone live only in backend environment variables.

Q: What is an environment variable?
A: Configuration supplied by the environment rather than hard-coded, which keeps secrets out of source control.

Q: What is CI/CD?
A: Continuous Integration and Continuous Deployment - automatically testing every push and deploying when tests pass. Mine is GitHub Actions plus Render.

Q: What is GitHub Actions?
A: GitHub's CI service. My workflow runs flake8, an import check, 70 pytest tests, a TypeScript check and a production build.

Q: What is Render?
A: The cloud host. It runs my FastAPI service and serves the built React app as a static site.

Q: What is Docker? Do you use it?
A: Docker packages an app with its dependencies into a container. I don't use it directly - Render builds from `render.yaml` and requirements.txt. I'd add a Dockerfile for reproducibility if I moved hosts.

Q: What is Pydantic?
A: A Python validation library that builds validators from type hints. FastAPI uses it to validate request bodies and return 422 automatically.

Q: What is an ASGI server?
A: The async equivalent of WSGI. Uvicorn is mine - it runs the FastAPI app and handles the event loop.

Q: What is `async`/`await` in Python?
A: A way to write concurrent I/O-bound code on a single thread - `await` yields control while waiting so other work can run.

Q: What is a React hook?
A: A function letting a component use state and lifecycle features. I have four custom ones: useAuth, useDocuments, useChat and useAudio.

Q: What is `useState` vs `useEffect`?
A: `useState` holds a value that triggers a re-render when changed. `useEffect` runs side effects after render, like subscriptions or data fetching.

Q: What is localStorage?
A: Browser key-value storage that persists across sessions. I keep the theme, guest chat history and the Supabase session there.

Q: What is a REST API?
A: An HTTP API where URLs identify resources and methods express actions. Mine is mostly RESTful, though `/api/query` is really an RPC-style streaming endpoint.

Q: What HTTP status codes does your API return?
A: 200, 400, 401, 403, 404, 413, 422, 502 and 503 - each mapped to a specific failure class.

Q: What is Row Level Security?
A: A Postgres feature where policies filter rows per user. Supabase evaluates `auth.uid()` from the JWT, so the database itself enforces isolation.

Q: What is multi-tenancy?
A: One application instance serving many users whose data must stay separated. Mine separates tenants by a `user_id` metadata filter in Pinecone and RLS in Postgres.

## Level 2 - Intermediate (50 questions)

Q: Why hybrid search instead of pure semantic?
A: Embeddings are weak on rare exact tokens like error codes and part numbers. BM25 rewards exactly those, because rarity drives IDF. Together they cover each other's blind spots.

Q: How do you combine the two scores?
A: `0.5 * cosine + 0.5 * min-max-normalised BM25`, over the twelve candidates Pinecone returned, then clamped to 0-1.

Q: Why normalise BM25 before combining?
A: Cosine is roughly bounded 0-1; raw BM25 is unbounded and query-dependent. Without normalisation BM25 would dominate the blend entirely.

Q: Is that hybrid retrieval or hybrid re-ranking?
A: Re-ranking. I re-score the dense candidates. A chunk BM25 would have loved but that dense search never returned is still invisible to me. True hybrid retrieval would query a sparse index in parallel and fuse the lists.

Q: Why retrieve 12 candidates for 4 results?
A: The reranker needs choices. ANN is approximate and the bi-encoder comparison is shallow, so the best passage is often ranked 5th or 7th.

Q: Why use an LLM as reranker?
A: I already had the client, key and retry logic, and it reasons about intent well. The cost is 400-1200ms and unstructured output I have to parse defensively. A dedicated cross-encoder would be faster and cheaper.

Q: Why HyDE?
A: Questions and passages are worded differently. Embedding a hypothetical answer produces a passage-shaped vector, and it expands short queries with related vocabulary.

Q: Why average the HyDE vector with the query vector?
A: To hedge. Pure HyDE bets everything on the hypothetical being on-topic; keeping 50% of the real query anchors the search if the model drifts.

Q: Why SSE over WebSockets?
A: I only need server-to-client push. SSE is plain HTTP, so normal auth, proxies and infrastructure work, and it has a built-in event format. WebSockets would add lifecycle management and framing for capability I don't use.

Q: Why fetch instead of EventSource?
A: `EventSource` can't set an Authorization header and only does GET. I need a Bearer token and a POST body, so I read the stream manually.

Q: How does authentication work end to end?
A: Supabase issues a signed JWT on login. The browser sends it as a Bearer header. The backend reads the `alg`, picks the matching key source - shared secret or JWKS - verifies the signature, checks `exp` and audience, and takes the `sub` claim as the user id.

Q: Why verify the JWT in the backend when Supabase already issued it?
A: Because anything the client sends is untrusted. Without signature verification, anyone could craft a token with any `sub` and read another user's documents. That was a real bug in an earlier version of this code.

Q: How does document isolation work?
A: Every vector carries the owner's `user_id` from a verified token. Every search applies an ownership filter that is never null. Client-supplied filename filters are AND-ed on top so they can only narrow. Deletion re-reads the stored owner and compares.

Q: What happens to an anonymous user's search?
A: It's filtered to the shared demo document only. Anonymous is a restricted identity, not an unfiltered one.

Q: How does chunk size affect retrieval quality?
A: Smaller chunks give precise vectors but fragmentary context; larger chunks give good context but blurry vectors that match too much. I use 750 characters plus sentence-window expansion to get both.

Q: Why 150 characters of overlap?
A: So a sentence cut by a chunk boundary still appears whole in at least one chunk. It costs about 20% more vectors.

Q: How do you preserve page numbers through chunking?
A: Chunking happens inside a page and never spans pages, so every chunk inherits exactly one page number, which goes into its metadata.

Q: Why store the chunk text in Pinecone metadata?
A: So retrieval returns the passage itself. Otherwise I'd need a second database round-trip to turn IDs into text.

Q: What is the chunk ID format and why does it matter?
A: `{document_id}_p{page}_c{index}`. It lets me derive neighbouring chunk IDs for context expansion, and enumerate a document's vectors by prefix for deletion.

Q: How does context expansion work?
A: For each final chunk I derive its neighbours' IDs, fetch them in one batched call, and stitch previous + current + next into one passage before generation.

Q: What happens at a page boundary in context expansion?
A: Nothing - the page number is fixed in the ID pattern, so it doesn't cross pages. That's a real limitation I'd fix with a document-global sequence number.

Q: Why does the router default to DOCUMENT_QUERY on failure?
A: The two errors aren't symmetric. Wrongly skipping retrieval gives an ungrounded answer with no citations; wrongly running it just wastes a lookup and falls back to a general prompt. The second is much cheaper.

Q: How do you handle a malformed reranker response?
A: JSON mode at temperature 0, then defensive parsing: handle None text, strip code fences, verify it's a dict, coerce each id in a try/except, bounds-check, de-duplicate. Anything unparseable falls back to hybrid ordering.

Q: How do you stop blocking the event loop?
A: Every blocking SDK call is wrapped in `asyncio.to_thread`. For the streaming path, a worker thread pushes chunks into an `asyncio.Queue` via `call_soon_threadsafe`.

Q: How do you handle client disconnection mid-stream?
A: `request.is_disconnected` is passed into the generator and checked before each token. On disconnect the generator returns, its `finally` sets a `threading.Event`, and the worker stops pulling from Gemini.

Q: How does the frontend know the stream finished properly?
A: A `complete` event sets a flag. If the reader loop ends without it, the code throws and shows "the response was interrupted" rather than saving a truncated answer.

Q: What happens if the SSE connection drops halfway?
A: Partial text stays on screen with an interruption note appended, and it is not persisted to Supabase as a finished answer. There's no automatic reconnect - replaying half an LLM answer would be worse than an honest error.

Q: How do you delete from Pinecone?
A: By enumerating IDs with a prefix list and deleting by ID in batches - not by metadata filter, which serverless indexes don't support. That was a real bug where deletes silently no-oped.

Q: How do you verify ownership before deleting?
A: I fetch the first enumerated chunk and compare its stored `user_id` with the caller. All chunks of a document come from one authenticated upload, so they share an owner, and `document_id` is a server-generated UUID so prefixes can't be forged.

Q: What is the difference between 401 and 403 in your API?
A: 401 means I can't establish who you are - missing, malformed or expired token. 403 means I know who you are and you're not allowed - like deleting someone else's document.

Q: Why 503 rather than 401 when JWKS is unreachable?
A: Because the token may be perfectly valid; the failure is on my side. Telling the user to sign in again would be wrong advice, and retrying might succeed.

Q: How does your config fail fast?
A: `pydantic-settings` validates at import time. A missing critical variable raises a ValidationError naming the field, so the process exits at startup instead of booting with placeholders and failing mysteriously later.

Q: Why is at least one of SUPABASE_JWT_SECRET or SUPABASE_URL required?
A: Because Supabase signs tokens either with a legacy shared secret or with asymmetric keys published via JWKS, and I support both. Without at least one I can't verify anything, so a model validator rejects that configuration.

Q: How do you handle Gemini rate limits?
A: Exponential backoff - up to 5 attempts at 2, 4, 8 and 16 seconds - but only for 429/quota errors. Deterministic errors re-raise immediately.

Q: What's missing from your backoff?
A: Jitter. Under concurrency, fixed delays cause a thundering herd where everyone retries at the same instants. Multiplying the delay by a random factor would fix it.

Q: What does your test suite actually assert?
A: JWT rejection for forged, expired, wrong-audience and `alg: none` tokens; the exact shape of ownership filters; that delete refuses non-owners and shared documents; BM25 edge cases; filename sanitisation; accent preservation; and the exact SSE event ordering including that GENERAL_CHAT emits no sources event.

Q: How do you test without hitting Pinecone or Gemini?
A: Fakes. A `FakeIndex` implements list, fetch and delete in memory; a stub Gemini client yields fixed text chunks; `conftest.py` sets placeholder env vars before any app import. The whole suite runs offline.

Q: How does the frontend prevent race conditions when switching users?
A: A `cancelled` flag in the load effect's cleanup, so a slow earlier request can't overwrite newer state, plus an AbortController that cancels any in-flight stream on identity change.

Q: Why capture `activeSessionId` at send time?
A: So tokens land in the conversation that asked the question even if the user switches tabs mid-stream. Reading the current value later would misroute them.

Q: Why is guest chat persistence skipped while streaming?
A: `chatSessions` changes on every token, so without the guard the entire history would be serialised to localStorage hundreds of times per answer.

Q: How do optimistic updates work in your delete flow?
A: The card is removed immediately for responsiveness, the previous list is kept, and if any step fails - the HTTP call or the Postgres delete - the list is restored. Hiding a document whose vectors are still searchable would be misleading.

Q: What is Row Level Security doing for you?
A: It lets the browser query Postgres directly with a public anon key safely, because the database filters rows by `auth.uid()`. Verified live: anonymous reads return zero rows and anonymous inserts are rejected.

Q: Why does the frontend also filter by user_id if RLS exists?
A: RLS is the security boundary; the explicit filter documents intent and keeps the query correct if a policy is ever relaxed. It's defence in depth, not the primary control.

Q: What are build-time vs runtime environment variables?
A: `VITE_*` variables are substituted into the bundle at build time, so changing one needs a rebuild and they're publicly visible. Backend variables are read at process start, so a restart suffices and they stay secret.

Q: Isn't your Supabase anon key exposed in the bundle?
A: Yes, and that's by design - it's a publishable key. It grants nothing on its own because RLS policies gate every row by `auth.uid()`. The keys that must stay secret - Gemini and Pinecone - are backend-only.

Q: How does the citation numbering work?
A: Positionally. The context blocks are numbered in order, and the prompt tells the model to cite by 1-based position. The frontend maps `[n]` to `sources[n-1]` with a bounds check.

Q: Can the model cite a source that doesn't exist?
A: It can emit `[7]` when there are four sources. The UI bounds-checks and renders that as plain text instead of a broken link.

Q: Why do only the latest assistant message's citations become clickable?
A: Because sources are stored per session, not per message - the list only ever holds the most recent retrieval. Making older messages clickable linked them to the wrong chunks, which was a real bug.

Q: What would you change to fix that properly?
A: Store sources on the message rather than the session, which means persisting them to Supabase alongside the message text.

Q: Why is the TTS cache written to a temp file first?
A: So an aborted request can't leave a truncated MP3 under a valid cache key. `os.replace` publishes atomically only after synthesis completes.

## Level 3 - Advanced (40 questions)

Q: How would you scale Pinecone retrieval to millions of vectors?
A: Namespaces per tenant so each query searches a smaller space and isolation is structural rather than filter-based; a paid tier with more pods or higher serverless throughput; and possibly dimensionality reduction, since I'm already truncating to 768. I'd also add a retrieval cache keyed by user and normalised query.

Q: How would you reduce end-to-end RAG latency?
A: Measure first. My guess at the ordering is reranking at 400-1200ms, HyDE generation at 500-1500ms, then Pinecone and the fetch at 50-150ms each. So: make HyDE conditional on query length, replace the LLM reranker with a small local cross-encoder, and run the router and embedding concurrently instead of sequentially.

Q: Which stages could run in parallel that currently don't?
A: Classification and the plain query embedding are independent - both could start immediately, and the embedding is discarded if the route turns out to be GENERAL_CHAT. The HyDE generation and the query embedding are also independent. That could remove several hundred milliseconds.

Q: How would you reduce Gemini costs?
A: Cache retrieval results and answers per user; make HyDE conditional; replace the LLM reranker with a local model; shrink the vision pass by only sending pages whose text layer looks sparse rather than every page; and use a cheaper model for classification.

Q: The vision pass sends every page to Gemini. Is that wasteful?
A: Yes, measurably. A 300-page text-only PDF makes 300 vision calls that add almost nothing over the text layer. I'd gate it: if `page.get_text()` returns substantial text and the page has no images, skip the vision call. That could cut ingestion cost by an order of magnitude on typical documents.

Q: How would you evaluate RAG quality?
A: Two layers. Retrieval: build a set of question/relevant-chunk pairs and measure recall@k, MRR and nDCG - that tells me whether the right passage was even retrieved. Generation: faithfulness (is every claim supported by the context) and answer relevance, scored by an LLM judge with human spot-checks. Frameworks like RAGAS package these. I don't have this today and it's my biggest gap.

Q: Without an eval set, how do you know your pipeline is any good?
A: I don't, rigorously - and I'd say that rather than invent numbers. I'm relying on published results for the individual techniques and on manual spot-checking. That's exactly why I wouldn't quote a percentage improvement for HyDE or the reranker.

Q: How would you detect hallucinations in production?
A: A faithfulness check - decompose the answer into claims and ask a model whether each is supported by the retrieved context, logging a score. Cheaper heuristics: n-gram overlap between the answer and the context, and flagging answers where the model cited nothing.

Q: How would you handle prompt injection properly?
A: Layer it. Keep the instruction defences, but add structural separation - put context in a clearly delimited block and use system instructions where the API supports them. Detect suspicious patterns in ingested text at upload time. Most importantly, keep the model powerless: no tools, no function calling, and isolation enforced at the query level before the model runs, so injection can corrupt an answer but not cross a tenant boundary.

Q: How would you handle 10,000 concurrent users?
A: Nothing about the current design survives that. In order: rate limiting first, or costs explode. Then horizontal scaling of the FastAPI service behind a load balancer - it's stateless apart from in-process caches, so that's straightforward. Move the embedding and TTS caches to Redis. Move ingestion to a background queue so uploads return immediately. Upgrade the Pinecone tier. Then reckon with Gemini quota, which is probably the real ceiling.

Q: What is the single biggest bottleneck?
A: The Gemini API. A document query makes up to four calls - classification, condensation, HyDE, reranking - plus generation. Quota and latency there dominate everything else.

Q: SSE connections are long-lived. What does that mean for scaling?
A: Each in-flight answer holds an open HTTP connection and a worker thread for the Gemini producer, for 5-20 seconds. That caps concurrency per instance well below a typical request-response service. With many concurrent streams I'd need more instances, and I'd want to bound the thread pool explicitly rather than relying on the default executor.

Q: How would you redesign ingestion for very large PDFs?
A: Make it asynchronous. Upload returns a job id immediately, a worker processes pages in batches and reports progress, and the frontend polls or subscribes. That removes the HTTP timeout ceiling and lets me retry individual page batches rather than the whole document. I'd also add a per-user page quota.

Q: What happens today if someone uploads a 500-page PDF?
A: It's under 25 MB so it's accepted, then makes ~500 vision calls in batches of 8. That's minutes of processing inside one HTTP request, which will hit Render's request timeout. Practically, large PDFs fail. The size cap limits the damage but doesn't solve it - async ingestion is the real fix.

Q: How would you support multiple embedding models or migrate between them?
A: Store the model name in each vector's metadata and never mix models in one index. To migrate: create a second index, re-embed everything with the new model, dual-write during the transition, then cut reads over and delete the old index. Silently swapping models in place would leave old and new vectors in incompatible spaces with no error.

Q: Your BM25 runs only over retrieved candidates. What does that miss?
A: Any chunk the dense search didn't return. If a user searches for a rare code that appears in exactly one chunk and the embedding doesn't surface that chunk in the top 12, BM25 never sees it. Real hybrid retrieval - Pinecone sparse-dense vectors, or a separate BM25 index fused with reciprocal rank fusion - would fix it.

Q: How would you implement reciprocal rank fusion?
A: Run dense and sparse retrieval independently, then score each document as the sum over lists of `1/(k + rank)` with k around 60. It's attractive because it needs no score normalisation - it only uses ranks, so incomparable score scales stop mattering.

Q: How would you make the router cheaper?
A: A small local classifier - even logistic regression over embeddings, trained on a few hundred labelled queries - would run in single-digit milliseconds with no API call. Or embed the query once and reuse that embedding for both classification and retrieval, which removes a whole call.

Q: What's the consistency risk between Pinecone and Postgres?
A: There's no transaction across them, so three divergences are possible: vectors indexed but no row, row deleted but vectors remain, and partial indexing. I handle each with rollback or UI reconciliation, but the clean fix is pgvector so a single Postgres transaction covers both.

Q: When would you switch from Pinecone to pgvector?
A: When transactional consistency with my metadata matters more than managed convenience, or when the cost curve crosses over. I already run Postgres via Supabase, so pgvector would remove a whole external dependency and let delete be atomic. The trade-off is operating the index myself and worse performance at very large scale.

Q: How would you add rate limiting?
A: A token bucket per user id in Redis, checked in FastAPI middleware, with different budgets for query and upload since upload is far more expensive. Return 429 with a `Retry-After` header. I'd also add a daily spend cap per user, because the real risk is cost rather than load.

Q: How would you make the system multi-region?
A: Hard, because Pinecone indexes are regional. I'd need per-region indexes with replication or accept cross-region latency for reads. Supabase has read replicas. Realistically I'd start by putting the stateless FastAPI service in multiple regions and keeping one data region, then measure whether the latency actually matters.

Q: What would you monitor in production?
A: Retrieval hit rate - how often DOCUMENT_QUERY returns zero sources. Route distribution, to know whether the router earns its cost. Per-stage latency percentiles. Gemini error and retry rates. Token spend per user. And 401/403 rates, since a spike suggests either a broken client or probing.

Q: How would you A/B test a retrieval change?
A: Offline first, on a fixed evaluation set, since that's cheap and repeatable. Online, I'd hash the user id to a bucket, log which variant served each query alongside a proxy for satisfaction - regeneration rate, follow-up rate, or explicit thumbs. Retrieval changes are hard to judge online without explicit feedback, which is why the offline set matters most.

Q: What's the security weakness you're least comfortable with?
A: The absence of rate limiting. Every other gap is bounded, but an authenticated user can currently issue unlimited queries, each costing several Gemini calls. That's a direct route to a large bill, and it's the first thing I'd add.

Q: Could a malicious PDF compromise your server?
A: The realistic vector is a parser vulnerability - PyMuPDF is C code, and a crafted PDF exploiting a memory bug would run in my process. I don't sandbox parsing. Mitigations would be running ingestion in a separate constrained worker, keeping PyMuPDF patched, and enforcing resource limits. The extension allow-list and size cap don't help against that class of bug.

Q: How do you know your isolation actually works, rather than just looking correct?
A: Tests plus a live check. Unit tests assert the exact filter shapes and that deletion refuses non-owners. I also ran a live check against the real Pinecone index: indexed documents under two synthetic users, confirmed each retrieved only their own, confirmed anonymous retrieved neither, confirmed a non-owner delete was refused and an owner delete actually removed the vectors.

Q: What happens if two users upload files with the same name?
A: Both index fine - documents are keyed by a server-generated UUID and scoped by `user_id`, so there's no collision or leakage. The wrinkle is within a single user: filters are by filename, so two same-named documents can't be distinguished in the filter UI. Filtering by `document_id` would fix it.

Q: What's your cold-start story?
A: Poor on Render's free tier - the service spins down after inactivity and the first request can take 50 seconds or more. Startup itself also lists and possibly creates the Pinecone index. A paid instance or an uptime pinger fixes it.

Q: Where would you add a queue and why?
A: Ingestion. It's the only genuinely long-running operation, it's naturally asynchronous from the user's point of view, and it needs per-batch retry. Query has to stay synchronous because the user is waiting.

Q: How would you support documents larger than the 25 MB limit?
A: Chunked or resumable upload to object storage, then a background job that streams the file page by page rather than holding it in memory. The current design reads the whole file into RAM, which is what really caps the size.

Q: How do you handle the ordering guarantee in SSE?
A: The generator is sequential, so events are yielded in a fixed order and HTTP preserves it within one response. The frontend doesn't assume ordering beyond that - it handles each event type independently, so an unexpected order degrades rather than breaks. There's a test asserting the exact sequence.

Q: What if Gemini returns tokens faster than the client consumes them?
A: The producer thread pushes into an unbounded `asyncio.Queue`, so it never blocks - memory grows with the backlog instead. For answer-sized responses that's a few hundred kilobytes at most. A bounded queue would apply backpressure but risks blocking the producer thread, so unbounded plus a stop flag was the simpler correct choice here.

Q: Your embedding cache is per-process. What breaks when you scale out?
A: Nothing breaks; it just gets less effective. Each instance builds its own cache, so hit rates drop roughly by the number of instances. Redis would fix it and would also give me a place for rate-limit counters.

Q: How would you handle GDPR-style deletion?
A: Deleting the auth user cascades the Postgres rows. Pinecone doesn't cascade, so I'd need a job that enumerates and deletes every vector for that user - which today means listing by each of their document ID prefixes, since I can't delete by metadata filter on serverless. Per-user namespaces would make this one call.

Q: What's the weakest part of your retrieval pipeline?
A: Probably that BM25 only re-scores dense candidates, so the pipeline inherits the dense retriever's recall ceiling. Second is having no evaluation set, which means every tuning decision - the 50/50 weight, top_k of 12, the rerank window of 8 - is a reasonable default rather than a measured optimum.

Q: If you rebuilt this from scratch, what would you change?
A: Three things. Postgres with pgvector instead of Pinecone, to get transactional consistency and drop a dependency. Asynchronous ingestion behind a queue. And an evaluation harness from day one, so retrieval changes could be measured instead of guessed at.

Q: What did you learn that surprised you?
A: How much of the work was outside the RAG algorithm. The retrieval pipeline is maybe a fifth of the effort. The rest was auth, tenant isolation, streaming without blocking the event loop, deletion actually working on serverless, and failure handling. The naive version of this project is a weekend; the correct version is not.

Q: What would you tell someone starting a similar project?
A: Decide your isolation model before you write any retrieval code, because retrofitting it means re-indexing everything. And check your vector database's actual limitations early - I assumed delete-by-filter worked because the SDK accepted the call, and it silently didn't on serverless.
'''


PART_30 = r'''
# Part 30 - Follow-Up Question Chains

Interviewers rarely stop at the first answer. These chains simulate being pushed on a topic
until it runs out. Read them as dialogues.

## Chain 1 - Pinecone and vector databases

Q: Why did you use Pinecone?
A: I needed approximate nearest-neighbour search over 768-dimension vectors with metadata filtering, and I didn't want to run infrastructure. Pinecone serverless gave me that with a free tier.

Q: Why not PostgreSQL?
A: Plain Postgres has no vector index, so it would sequentially scan every row computing 768-dimension dot products. With the pgvector extension it's a genuine alternative, and honestly a strong one for my scale.

Q: So why didn't you use pgvector? You already run Postgres through Supabase.
A: Fair challenge. The main reason was managed convenience and not wanting to tune an index. The strongest argument for pgvector is that I'd get transactional consistency - today a document lives in Pinecone and Postgres with no transaction across them, so they can diverge.

Q: What exactly does Pinecone store?
A: One record per chunk: an ID, 768 floats, and a metadata dictionary containing document_id, filename, chunk_id, page_number, upload_time, source_type, user_id and the chunk's full text.

Q: Why store the text in the vector database?
A: So retrieval returns the passage directly. Otherwise every query would need a second round-trip to some other store to turn IDs into text.

Q: What does the vector actually represent?
A: The meaning of that chunk, as positioned by the embedding model. Chunks with similar meanings sit close together in that 768-dimension space.

Q: How does Pinecone find similar vectors quickly?
A: An approximate nearest-neighbour index - graph or clustering based - so it doesn't compare against every vector. You trade a small amount of recall for a very large speed gain.

Q: What similarity metric do you use?
A: Cosine.

Q: Why cosine and not Euclidean or dot product?
A: Cosine measures direction and ignores magnitude, and in text embeddings magnitude tends to track length rather than meaning. Dot product would let long chunks dominate. Euclidean distance is sensitive to magnitude the same way.

Q: Does the metric have to match how the embeddings were trained?
A: Ideally yes - you want the metric the model was optimised for. Gemini's embeddings are intended for cosine, and the Pinecone index is created with cosine, so they agree.

Q: What happens if you change embedding model but keep the same dimension?
A: That's the dangerous case. Nothing errors - dimensions still match - but old and new vectors live in incompatible spaces, so retrieval quality silently collapses. You'd have to re-index everything.

Q: How would you do that migration with no downtime?
A: Build a second index, re-embed the corpus into it, dual-write new uploads to both, then flip reads once it's caught up, and delete the old index. I'd also put the model name in metadata so a mixed state is at least detectable.

## Chain 2 - Embeddings

Q: What is an embedding?
A: A fixed-length list of numbers representing the meaning of text, such that similar meanings give similar vectors.

Q: Where do the numbers come from?
A: A neural network trained so that texts appearing in similar contexts get similar vectors. Nobody designs the dimensions; they're learned.

Q: Can you interpret an individual dimension?
A: Generally no. Meaning is distributed across all 768. You can find directions that correlate with concepts, but no single axis is "formality" or "topic".

Q: How many dimensions do you use and why?
A: 768. It has to match the Pinecone index exactly. `gemini-embedding-001` natively produces 3072 and supports truncation, and 768 cuts storage and query cost about fourfold for a modest quality loss.

Q: Is truncating a 3072-dimension embedding to 768 safe?
A: The model supports it explicitly through `output_dimensionality`, and it's trained so the leading dimensions carry the most information - Matryoshka-style. It's not the same as naively slicing an arbitrary embedding.

Q: Do you normalise the vectors?
A: No, and with cosine I don't need to - cosine divides by the magnitudes, so ranking is unaffected. It would matter if the index used dot product.

Q: You use different task types for queries and documents. Why?
A: Because retrieval is asymmetric - a short question should land near a long passage that answers it, even though they're worded completely differently. `RETRIEVAL_QUERY` and `RETRIEVAL_DOCUMENT` tell the model which side it's embedding.

Q: What would happen if you used the same task type for both?
A: It would degrade. You'd effectively be measuring "how similar is this text to that text", which favours passages phrased like questions rather than passages that answer them.

Q: How do you handle the API's batch limits?
A: Batches of 64 chunks per request, and I assert the returned count matches the batch size.

Q: Why is that assertion important?
A: Because embeddings are matched to chunk metadata by list index. A silent mismatch would attach every chunk's text to the wrong page number - corrupt citations with no error anywhere.

## Chain 3 - RAG fundamentals

Q: What is RAG?
A: Retrieve relevant passages, put them in the prompt, generate an answer from them.

Q: Why not fine-tune a model on the documents instead?
A: Different tools. Fine-tuning teaches style and format, not facts you can cite; it needs retraining for every new document, and you still can't attribute an answer to a page. RAG updates instantly - upload and it's searchable - and gives verifiable sources.

Q: When would fine-tuning be better?
A: When you need a consistent output format or domain tone, or when the task is a skill rather than a lookup. They're complementary - you could fine-tune for style and still retrieve for facts.

Q: Why not just use a model with a million-token context and skip retrieval?
A: Cost and quality. You'd pay for the whole corpus on every single query, latency scales with input, and models measurably degrade at finding a specific fact buried in a huge context. Retrieval also gives you citations, which a long context does not.

Q: What's the failure mode of RAG?
A: Retrieval misses. If the right passage isn't in the top-k, the model either says it doesn't know or answers from general knowledge. The generation step can't fix bad retrieval - which is why most of my pipeline is about retrieval quality.

Q: How would you know retrieval missed?
A: Today I mostly wouldn't, which is a real gap. The signal I do have is DOCUMENT_QUERY returning zero sources. Properly, I'd need an evaluation set measuring recall@k.

## Chain 4 - Chunking

Q: Why chunk?
A: Embedding limits, retrieval precision, and citation granularity.

Q: How did you pick 750 characters?
A: It's a reasonable default rather than a tuned value - large enough to be a coherent passage, small enough that four fit comfortably in a prompt. I'd tune it against an evaluation set if I had one.

Q: What would you tune it against?
A: Recall@k on a set of question/relevant-passage pairs, plus a cost term for the number of vectors. I'd expect the optimum to differ by document type - dense technical text wants smaller chunks than narrative prose.

Q: Why character-based rather than token-based chunking?
A: Simplicity - `len()` needs no tokeniser. The downside is that 750 characters is a different number of tokens in English versus a script like Tamil, so chunks aren't uniform in the unit that actually matters for cost.

Q: Would semantic chunking be better?
A: Probably, for quality. Splitting on topic shifts rather than character counts keeps ideas intact. The costs are that it needs embeddings during ingestion to detect the shifts, it's slower, and chunk sizes become unpredictable, which complicates prompt budgeting.

Q: How do you stop a chunk from cutting a sentence in half?
A: Two ways. The recursive splitter prefers paragraph and line breaks over arbitrary cuts, and 150 characters of overlap mean a boundary-straddling sentence appears complete in one of the two chunks. Sentence-window expansion then repairs the rest at query time.

## Chain 5 - Agentic routing

Q: What makes your project agentic?
A: An LLM decides the control flow - whether to run retrieval at all - rather than the pipeline being fixed.

Q: Is that really an agent?
A: Not in the strong sense. No tool loop, no planner, no self-correction. It's a classifier in the control flow plus a query rewriter. I'd rather describe it accurately than lean on the term.

Q: So why use the word at all?
A: Because "the LLM makes a routing decision" is a meaningful architectural difference from fixed-pipeline RAG, and "agentic RAG" is the common name for it. But I'd immediately qualify what it does and doesn't do.

Q: What would make it genuinely agentic?
A: A loop where the model can evaluate its own retrieval and act on it - if the passages look weak, reformulate the query and search again, or decide it needs a different tool. That's Self-RAG or CRAG territory.

Q: Why not implement that?
A: Cost and latency mostly - each extra loop is another LLM call and another second or two, and it needs a reliable way to judge retrieval quality, which is its own problem. It's the most interesting extension though.

Q: What happens when your router is wrong?
A: Asymmetric consequences. Wrongly choosing GENERAL_CHAT gives an ungrounded answer with no citations. Wrongly choosing DOCUMENT_QUERY just wastes a retrieval and falls back to a general prompt. That asymmetry is why the failure default is DOCUMENT_QUERY.

Q: How often is it wrong?
A: I haven't measured it, and I wouldn't guess. To find out I'd log the classification alongside whether retrieval returned anything useful, and hand-label a sample.

## Chain 6 - SSE and streaming

Q: Why stream at all?
A: Generation takes 5-20 seconds. Streaming makes the first word appear in about a second, which changes the perceived speed completely even though total time is the same.

Q: Why SSE rather than WebSockets?
A: One direction is all I need. SSE is plain HTTP, so auth headers, proxies and load balancers all just work, and it has a message format built in.

Q: Why not use the EventSource API then?
A: It can't set an Authorization header and it can't POST. I need a Bearer token and a JSON body, so I read the stream with fetch and parse the format myself.

Q: What do you lose by not using EventSource?
A: Automatic reconnection and the Last-Event-ID replay mechanism. For LLM output that's fine - silently resuming half an answer would be worse than an honest error message.

Q: How do you parse the stream?
A: Accumulate decoded text in a buffer, split on the double newline, process complete packets and put the trailing fragment back in the buffer.

Q: Why does the trailing fragment matter?
A: Because TCP doesn't respect message boundaries. A read can deliver two and a half events. Without keeping the partial one you'd get JSON parse errors - and typically only under load, never in testing.

Q: What happens if the model outputs something that breaks your format?
A: It can't, because I never put raw model text in the SSE frame - it goes through `json.dumps`, which escapes newlines and quotes. That's why the payload is JSON rather than bare text.

Q: How do you handle an error once streaming has started?
A: I can't change the status code - headers are already sent. So errors become in-stream events: a generic error token and then `complete` with status error. The detail is logged server-side, never sent to the client.

## Chain 7 - Authentication and isolation

Q: How do you authenticate requests?
A: A Supabase-issued JWT in an Authorization header, whose signature the backend verifies before trusting any claim.

Q: Why verify it yourself? Supabase issued it.
A: Because the token arrives from the client, and anything from the client is untrusted. Without verification anyone could forge a token with any `sub`. That was an actual bug in an earlier version of this code - it base64-decoded the payload and trusted it.

Q: How do you verify it?
A: Read the `alg` from the header, pick the matching key source - the shared HS256 secret or the project's JWKS for ES256/RS256 - then decode with that single algorithm, requiring `exp` and `sub` and checking the audience.

Q: Reading `alg` from an unverified header is a classic vulnerability. Why is that safe?
A: Because the algorithm only chooses a key *source*, and each source is bound to one family. HS256 always uses the shared secret and never a JWKS key, so signing a token with the published public key as an HMAC secret fails. `alg: none` isn't in either allow-list.

Q: What if the JWKS endpoint is down?
A: I return 503, not 401. The token may be entirely valid; the failure is mine. Telling the user to sign in again would be wrong advice.

Q: Once you have the user id, how do you enforce isolation?
A: Every vector carries the owner's id in metadata, and every Pinecone query applies an ownership filter that is never null.

Q: What about the filename filters the UI sends?
A: They're AND-ed with the ownership filter, never substituted. A client-supplied filter can only narrow the result set, never widen it.

Q: What if I send a filter for a filename I don't own?
A: You get nothing. The ownership clause still applies, so the intersection is empty.

Q: What if I pass someone else's document_id to the delete endpoint?
A: 403. The service enumerates that document's vectors, reads the stored owner off the first one, and compares it to your verified user id before deleting anything.

Q: Why is checking one chunk enough?
A: All chunks of a document are written by one authenticated upload, so they share an owner. And `document_id` is a server-generated UUID, so you can't craft one that collides with someone else's prefix.

Q: Have you actually tested this, or does it just look right?
A: Both. There are unit tests on the filter shapes and the delete authorization, and I ran a live check against the real index with two synthetic users confirming each retrieved only their own documents, anonymous retrieved neither, and a non-owner delete was refused.

## Chain 8 - Reranking

Q: Why do you rerank?
A: Because vector search is approximate and shallow - the query and passage were embedded separately and compared with one dot product. Reranking looks at them together.

Q: What's the difference between a bi-encoder and a cross-encoder?
A: A bi-encoder embeds each side independently, so passage vectors can be precomputed - fast but shallow. A cross-encoder feeds query and passage in together so the model can attend across them - much more accurate, but nothing can be precomputed.

Q: So why not cross-encode everything?
A: Because you'd have to run the model once per passage at query time. Over a whole corpus that's impossible. Hence two stages: cheap and wide, then expensive and narrow.

Q: You're using an LLM, not a real cross-encoder. Does that matter?
A: It matters for cost and latency. A trained cross-encoder like ms-marco-MiniLM runs in tens of milliseconds locally; my Gemini call is several hundred milliseconds and costs money. I used the LLM because it was zero extra infrastructure and reasons well about intent, but I'd call it "cross-encoder style" rather than a cross-encoder.

Q: How do you handle the LLM returning bad output?
A: JSON mode at temperature zero, then parse defensively - None text, code fences, non-dict JSON, non-integer ids, out-of-range ids and duplicates are all handled. Anything unparseable falls back to hybrid ordering.

Q: What if it returns an empty list?
A: I treat that as "no strong preference" and keep the hybrid order rather than returning zero sources. Returning nothing would make the answer ungrounded because the model declined to rank.

Q: How would you know reranking is actually helping?
A: I'd need the evaluation set again - compare recall@4 and nDCG with the reranker on and off. I don't have that, so I'm relying on it being a well-established technique rather than on my own measurement.
'''


PART_31 = r'''
# Part 31 - "Why Did You Use This?" - Technology Decisions

| Technology | Why we used it | Alternatives | Why not the alternative |
|---|---|---|---|
| **React 18** | Component model fits a chat UI with many independent pieces of state; huge ecosystem; hooks let me isolate all logic away from presentation | Vue, Svelte, plain JS | Not better for this; React is what I know well and what most teams use. Plain JS would mean hand-managing streaming DOM updates |
| **TypeScript** | Catches contract mismatches at build time - especially between the SSE payloads and the frontend types; `tsc` runs before every build | Plain JavaScript | With four hooks sharing state and a typed API contract, untyped code would have cost more time than it saved |
| **Vite** | Very fast dev server, simple config, built-in env handling | Create React App, Next.js | CRA is deprecated. Next.js adds SSR and routing I don't need for a single-page authenticated app |
| **Tailwind CSS** | Dark mode via a single class strategy; no separate stylesheet to keep in sync with components | CSS Modules, styled-components | Both mean more files and more context switching for a UI this size |
| **FastAPI** | Native async for SSE; Pydantic validation from type hints; dependency injection is exactly how I inject auth | Flask, Django, Express | Flask's async support is bolted on and SSE with auth would be manual. Django is far too heavy for four endpoints. Express would mean a second language |
| **Uvicorn** | ASGI server FastAPI is designed for; handles the event loop | Gunicorn alone, Hypercorn | Gunicorn is WSGI - it can't run async natively without an ASGI worker |
| **Pydantic v2** | Request validation, automatic 422s, and `pydantic-settings` gives fail-fast config | Manual validation, marshmallow | Manual validation is where security bugs live. Pydantic is already FastAPI's dependency |
| **Google Gemini 2.5 Flash** | One provider covering vision, chat, embeddings and reranking; generous free tier; fast | OpenAI GPT-4o, Claude, Llama | Cost and the free tier, mainly. Flash is optimised for latency, which matters for streaming. A larger model would answer better but slower and dearer |
| **gemini-embedding-001** | Same provider and SDK as generation; supports truncation to 768 dims and retrieval-specific task types | OpenAI text-embedding-3, open models via sentence-transformers | Fewer providers to manage. Self-hosting embeddings would mean running a GPU or accepting slow CPU inference |
| **Pinecone** | Managed ANN with metadata filtering - filtering is what my whole isolation model rests on; serverless free tier; index auto-created at startup | pgvector, Weaviate, Qdrant, Chroma | pgvector is the strongest alternative and would give transactional consistency; I chose managed to avoid operating an index. Chroma isn't built for a hosted multi-user service |
| **Supabase** | Production auth - email, Google OAuth, refresh - plus Postgres and RLS, on a free tier | Auth0, Firebase, custom JWT auth | Custom auth is the riskiest thing a student can hand-roll. Auth0 doesn't bring a database. Firebase would mean a NoSQL model and Google lock-in for data too |
| **Supabase RLS** | Lets the browser query Postgres directly and safely, so I don't need CRUD endpoints for documents and chat | Backend endpoints for everything | Would mean writing and securing a dozen more endpoints that RLS already handles at the database level |
| **SSE** | One-directional push over plain HTTP; works with Bearer auth and normal proxies; named events carry metadata and sources | WebSockets, long polling, plain response | WebSockets are bidirectional complexity I don't use. Long polling wastes requests. A plain response means 15 seconds of blank screen |
| **fetch + ReadableStream** | Lets me send an Authorization header and a POST body, which EventSource cannot | EventSource | Would force the token into the URL and the payload into query params |
| **BM25 (hand-written)** | ~40 lines over 12 candidates; no dependency; forced me to actually understand k1, b and IDF | rank_bm25, Elasticsearch | A dependency for 40 lines wasn't worth it. Elasticsearch is an entire second datastore |
| **HyDE** | Bridges the question/passage phrasing gap and expands short queries | Plain query embedding, multi-query expansion | Plain embedding is what I fall back to. Multi-query means several searches and even more latency |
| **Gemini as reranker** | Zero extra infrastructure - same client, key and retry path | ms-marco cross-encoder, Cohere Rerank | A local cross-encoder would be faster and cheaper and is the upgrade I'd make. Cohere means another vendor and key |
| **LangChain text splitters** | Just the splitter package - a well-tested recursive splitter | Full LangChain, hand-written splitter | I deliberately removed `langchain` and `langchain-community` from requirements; only the splitter is used. The full framework is a large dependency for one class |
| **PyMuPDF** | Fast, accurate text extraction and page rasterisation in one library | pdfplumber, PyPDF2, pdfminer | PyPDF2 can't render pages to images, which I need for the vision pass. pdfplumber is slower for large documents |
| **edge-tts** | Neural voices in many languages with no API key and no cost | Azure Speech, Google Cloud TTS, browser speechSynthesis | The paid services need billing setup. Browser TTS voices are far lower quality and vary by OS. The honest downside is that edge-tts is unofficial with no SLA |
| **Web Speech API** | Zero cost, zero keys, no audio through my server | Whisper API, self-hosted Whisper | Whisper means uploading audio, paying per minute and adding latency. Browser recognition is instant and free - at the cost of Chromium-only support |
| **PyJWT** | Standard, well-audited JWT library supporting both HS256 and JWKS-based ES256/RS256 | python-jose, hand-rolled verification | Hand-rolling JWT verification is how algorithm-confusion vulnerabilities happen. python-jose has had maintenance concerns |
| **Render** | Both services from one `render.yaml`, free tier, HTTPS, health checks, cross-service env injection | Vercel + Railway, AWS, Fly.io | AWS is far more setup than this needs. Splitting frontend and backend across two providers means two dashboards and manual URL wiring |
| **GitHub Actions** | Already on GitHub; free for public repos; simple YAML | CircleCI, Jenkins, GitLab CI | No reason to add a second platform |
| **pytest** | Standard, minimal boilerplate, good fixtures | unittest | unittest is more verbose for the same coverage |

## The three decisions most worth defending

**1. Pinecone over pgvector.** The honest answer includes the counterargument: *"I chose
managed to avoid operating an index, but I already run Postgres via Supabase, so pgvector
would have given me transactional consistency between the document row and its vectors -
which is a real gap in my current design."*

**2. SSE over WebSockets.** *"I only need one direction. Choosing WebSockets would be
selecting the more capable protocol for capability I don't use, and paying for it in
connection lifecycle code, framing and proxy compatibility."*

**3. LLM reranker over a dedicated model.** *"Pragmatic, not optimal. It cost me nothing to
add and it's the slowest stage in my pipeline. If I were optimising latency it's the first
thing I'd replace with a local cross-encoder."*

KEY: In every one of these, naming the cost of your own choice is what makes the answer credible. An engineer who can only list benefits hasn't really evaluated the decision.
'''
