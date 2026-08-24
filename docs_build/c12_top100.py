PART_41 = r'''
# Part 41 - The 100 Most Likely Questions

Ranked by how likely an interviewer who has skimmed your repository is to ask. Each has a
short answer to lead with, a longer answer if they push, and the follow-up to expect.

## Opening and framing (1-10)

Q: 1. Tell me about this project.
A: **Short:** A full-stack RAG app - upload documents, chat with them, get answers with page-level citations. React and TypeScript front end, FastAPI backend, Gemini for AI, Pinecone for vectors, Supabase for auth, deployed on Render.
A: **Long:** Use the Part 2 script - name the stack, then the three things you're proud of: multi-stage retrieval, multi-tenant isolation, and non-blocking streaming.
FU: Which part was hardest?

Q: 2. Why did you build it?
A: **Short:** I wanted to build a RAG system that wasn't a notebook demo - one with real auth, real tenant isolation and real deployment.
A: **Long:** Anyone can do embed-search-generate in fifty lines. The interesting work was stopping user A reading user B's documents, making deletion actually work on a serverless vector DB, and streaming without blocking the server.
FU: What did you learn that surprised you?

Q: 3. What does "Agentic" mean here?
A: **Short:** An LLM classifies each query and decides whether to run retrieval at all, and rewrites follow-up questions into standalone ones.
A: **Long:** Two behaviours - routing between GENERAL_CHAT and DOCUMENT_QUERY, and query condensation against history. That's it. It is not an autonomous agent with tools, planning or self-correction, and I wouldn't claim otherwise.
FU: So is it really an agent?

Q: 4. What does "Multimodal" mean here?
A: **Short:** PDF pages are processed as both text and image - PyMuPDF for the text layer, Gemini Vision on a 150 DPI render for tables, charts and layout.
FU: Is that OCR?

Q: 5. What was the hardest part?
A: **Short:** Document deletion. Serverless Pinecone doesn't support delete-by-metadata-filter, the SDK accepts the call anyway, and my frontend wasn't checking the response - so deletes silently did nothing.
A: **Long:** See Part 2. Mention the ID-prefix enumeration fix and that ownership verification came along with it.
FU: How did you find it?

Q: 6. What would you do differently?
A: **Short:** pgvector instead of Pinecone for transactional consistency, asynchronous ingestion behind a queue, and an evaluation harness from day one.
FU: Why pgvector specifically?

Q: 7. What are you most proud of?
A: **Short:** That the isolation model is enforced server-side at every layer and I have tests plus a live cross-tenant check proving it.
FU: Show me how it's enforced.

Q: 8. How long did it take?
A: Answer honestly with your real timeline, and split it: the RAG pipeline was a fraction of the work; auth, isolation, streaming and failure handling took the majority.

Q: 9. Did you use AI to build it?
A: Be honest. The good framing: "Yes, for scaffolding and review. The parts I can explain line by line are the ones that matter, and this handbook exists because I can." Never claim you wrote something you can't explain.

Q: 10. What's the one thing wrong with it?
A: **Short:** No rate limiting. Every document query is up to five Gemini calls and nothing caps a user, which is a direct route to a large bill.
FU: How would you add it?

## RAG fundamentals (11-25)

Q: 11. What is RAG?
A: Retrieve relevant passages from a knowledge store, put them in the prompt, generate an answer grounded in them.
FU: Why is that better than a plain LLM?

Q: 12. Why not fine-tune instead?
A: Fine-tuning teaches style, not citable facts; it needs retraining per document and can't attribute an answer to a page. RAG updates instantly and gives sources.
FU: When would fine-tuning win?

Q: 13. Why not use a huge context window?
A: You'd pay for the whole corpus on every query, latency scales with input, models degrade at finding facts buried in long contexts, and you still get no citations.

Q: 14. What's the failure mode of RAG?
A: Retrieval misses. Generation can't fix bad retrieval - which is why most of my pipeline is retrieval quality.
FU: How would you detect a miss?

Q: 15. Walk me through your RAG pipeline.
A: Route, condense, HyDE embed, Pinecone top-12, BM25 blend, rerank to 4, expand neighbours, grounded prompt, stream. Seven stages - see Part 2.
FU: Why so many stages?

Q: 16. What is an embedding?
A: 768 numbers representing meaning, arranged so similar meanings are close.
FU: What model, and why 768?

Q: 17. What is cosine similarity?
A: The cosine of the angle between two vectors - dot product over the product of magnitudes. Ignores length.
FU: Why ignore length?

Q: 18. Why chunk documents?
A: Embedding input limits, retrieval precision, and citation granularity.
FU: How did you pick 750?

Q: 19. Why overlap chunks?
A: So a sentence cut at a boundary still appears whole in one chunk. 150 characters, about 20%.

Q: 20. What's in your metadata?
A: document_id, filename, chunk_id, page_number, upload_time, source_type, user_id, and the chunk text itself.
FU: Why store the text in the vector DB?

Q: 21. What is semantic search?
A: Matching by meaning rather than characters - "live longer" finds "longevity".

Q: 22. What is a vector database?
A: A store optimised for approximate nearest-neighbour queries over high-dimensional vectors.
FU: Why can't Postgres do that?

Q: 23. What is top_k?
A: How many nearest vectors to return. I request 12 and finish with 4.
FU: Why three times?

Q: 24. What is a token?
A: Roughly three-quarters of a word - the unit models read and bill for.

Q: 25. What's the difference between retrieval and generation?
A: Retrieval finds text - cheap, factual. Generation writes prose - expensive, fluent. RAG is retrieval then generation.

## Retrieval depth (26-45)

Q: 26. What is HyDE and why use it?
A: Generate a hypothetical answer, embed it, and search with it - because a fake answer looks more like the passages you're searching than the question does.
FU: Is it always better?

Q: 27. Why average the HyDE and query vectors?
A: To hedge against an off-topic hypothetical. 50/50 keeps the search anchored to the real question.

Q: 28. What if HyDE generation fails?
A: It returns the raw query, fusion is skipped, and the plain query embedding is used. There's a second guard around the HyDE embedding call too.

Q: 29. What is BM25?
A: Keyword ranking using term frequency with saturation, inverse document frequency, and length normalisation. k1 = 1.5, b = 0.75.
FU: What do k1 and b control?

Q: 30. Why blend BM25 with semantic search?
A: Embeddings are weak on rare exact tokens like error codes; BM25 rewards exactly those.
FU: Give me a concrete example.

Q: 31. How do you combine the scores?
A: 0.5 times cosine plus 0.5 times min-max normalised BM25, then clamped to 0-1.
FU: Why normalise?

Q: 32. Why 50/50?
A: It's a reasonable default, not a tuned value - I have no evaluation set to tune against, and I'd rather say that than invent a justification.

Q: 33. Is that hybrid retrieval or hybrid re-ranking?
A: Re-ranking. BM25 only sees the twelve candidates dense search returned, so I inherit the dense retriever's recall ceiling.
FU: How would you fix that?

Q: 34. What happens if all BM25 scores are equal?
A: The range is zero, so normalisation returns 0.0 for everything and ranking falls back to pure cosine. No divide-by-zero.

Q: 35. What is reranking?
A: A second, more accurate scoring pass over a small candidate set.
FU: Why not just retrieve 4 directly?

Q: 36. Bi-encoder vs cross-encoder?
A: A bi-encoder embeds each side separately so vectors can be precomputed - fast, shallow. A cross-encoder processes query and passage together - accurate, but nothing can be precomputed.

Q: 37. Why use an LLM as the reranker?
A: Zero extra infrastructure. The cost is 400-1200ms, which makes it the slowest stage - a local cross-encoder would be the upgrade.

Q: 38. How do you parse the reranker's output safely?
A: JSON mode at temperature 0, then handle None text, code fences, non-dict JSON, non-integer ids, out-of-range ids and duplicates. Anything unparseable falls back to hybrid order.

Q: 39. What is sentence-window retrieval?
A: Retrieve on small chunks for precision, then expand the winners with their neighbours before generation for context.

Q: 40. How do you find neighbouring chunks?
A: The chunk ID encodes it - `{document_id}_p{page}_c{index}` - so neighbours are derivable by string arithmetic and fetched by ID.
FU: What about the first chunk on a page?

Q: 41. What's the limitation of your context expansion?
A: It doesn't cross page boundaries, because the page number is fixed in the ID pattern.

Q: 42. Why retrieve 12 and rerank only 8?
A: 12 gives the hybrid scorer room; 8 bounds the rerank prompt size and latency.

Q: 43. How much context reaches the model?
A: Four passages of up to ~2250 characters each after expansion - roughly 2,250 tokens, versus 760 unexpanded.

Q: 44. What if retrieval returns nothing?
A: An empty sources event is still emitted, the prompt falls through to an honest ungrounded version, and the citations panel shows a "No Matching Sources" state.

Q: 45. How do you know retrieval is any good?
A: I don't, rigorously - there's no evaluation set. That's my biggest gap and I'd build one with 50-100 labelled question/passage pairs measuring recall@k and MRR.

## Architecture and backend (46-62)

Q: 46. Why FastAPI?
A: Native async for SSE, Pydantic validation from type hints, and dependency injection that's exactly how I inject auth.

Q: 47. Why separate routes from services?
A: Testability, reusability - my seeding script uses the services with no FastAPI - and single responsibility. Routes translate domain exceptions into HTTP status codes.

Q: 48. How are services instantiated?
A: Once, in a FastAPI `lifespan` handler, and stored on `app.state`. Rebuilding SDK clients per request would add TLS handshakes to every call.

Q: 49. Why `asyncio.to_thread` everywhere?
A: Because the Pinecone and Gemini SDKs are synchronous. Calling them directly in an async endpoint blocks the shared event loop, so one user's embedding call freezes everyone.
FU: How did you handle the streaming case?

Q: 50. How do you stream without blocking?
A: A worker thread iterates the blocking Gemini generator and pushes chunks into an `asyncio.Queue` with `call_soon_threadsafe`; the async generator awaits the queue. A `threading.Event` stops the worker if the client disconnects.

Q: 51. Why SSE not WebSockets?
A: One direction is all I need. SSE is plain HTTP so auth, proxies and load balancers work unchanged.
FU: Why not EventSource?

Q: 52. What are your SSE events?
A: metadata, sources, token, complete - in that order. GENERAL_CHAT emits no sources event, which is asserted by a test.

Q: 53. How does the client parse the stream?
A: Buffer decoded text, split on the double newline, process complete packets, keep the trailing fragment for the next read.
FU: Why keep the fragment?

Q: 54. How do you handle errors mid-stream?
A: Headers are already sent so I can't change the status. Errors become an in-stream generic error token plus `complete` with status error. Detail is logged, never sent.

Q: 55. What's your configuration strategy?
A: `pydantic-settings` validated at import. Missing critical variables abort startup with the field name, rather than booting with placeholders.
FU: Which variables are required?

Q: 56. Why does your config require one of two Supabase variables?
A: Because Supabase signs tokens either with a legacy shared secret or asymmetric keys via JWKS. I support both, and a model validator rejects a config with neither.

Q: 57. How do you handle rate limits?
A: Exponential backoff at 2/4/8/16 seconds over 5 attempts, but only for 429/quota errors - deterministic errors re-raise immediately.
FU: What's missing?

Q: 58. What's your fallback strategy?
A: Every optional stage degrades to the system without it - HyDE, reranking and context expansion are all quality improvements that cannot take the system down.

Q: 59. What HTTP status codes do you return and when?
A: 400 bad file, 401 unauthenticated, 403 not owner, 404 not indexed, 413 too large, 422 validation, 502 downstream failure, 503 JWKS unreachable.
FU: Why 503 rather than 401 for JWKS?

Q: 60. What does your logging look like?
A: Module-level loggers to stdout with timestamps and levels, noisy dependencies turned down to WARNING. I replaced every `print` in the services.

Q: 61. What would you add for observability?
A: Per-stage latency timings, route split, retrieval hit rate, Gemini retry rate, and token spend per user - which is exactly the data I'd need to optimise.

Q: 62. How do you test the backend without network access?
A: Fakes. A `FakeIndex` implementing list/fetch/delete in memory, a stub Gemini client yielding fixed chunks, and a conftest that sets placeholder env vars before any app import.

## Security (63-78)

Q: 63. How does authentication work?
A: Supabase issues a signed JWT; the browser sends it as a Bearer token; the backend verifies the signature, expiry and audience before trusting the `sub` claim.

Q: 64. Why verify the token server-side?
A: Because anything from the client is untrusted. Without verification anyone could forge a token with any user id - which was a real bug in an earlier version of this code.
FU: What did the old code do?

Q: 65. Which signing algorithms do you support?
A: HS256 with a shared secret, and ES256/RS256 verified against the project's JWKS. `alg: none` and anything else is rejected by allow-list.

Q: 66. You read `alg` from an unverified header - isn't that the classic JWT vulnerability?
A: It would be if the algorithm chose the key. It only chooses a key *source*, and each source is bound to one family - HS256 never uses a JWKS key. So signing with the published public key as an HMAC secret fails. There's a test for it.

Q: 67. Authentication vs authorization?
A: Authentication is who you are - 401 on failure. Authorization is what you may do - 403. Deleting someone else's document with a valid token is 403.

Q: 68. How do you isolate tenants?
A: Every vector carries the owner's verified user id; every query applies an ownership filter that is never null; client filename filters are AND-ed on top so they can only narrow; deletion re-reads the stored owner.

Q: 69. What does an anonymous user see?
A: The shared demo document only. Anonymous is a restricted identity, not an unfiltered one - the original code passed `None` as the filter, which matched every tenant's vectors.

Q: 70. Can a user delete someone else's document?
A: No. The service enumerates the document's vectors, reads the owner off the first one, and raises PermissionError - 403 - if it doesn't match. Nothing is deleted.

Q: 71. Why is checking one chunk's owner enough?
A: All chunks of a document come from one authenticated upload, so they share an owner, and `document_id` is a server-generated UUID so prefixes can't be forged.

Q: 72. What is Row Level Security doing?
A: Letting the browser query Postgres directly and safely. Policies filter by `auth.uid()`, so an anonymous read returns zero rows - verified live against the deployed project.

Q: 73. Your Supabase anon key is in the JS bundle. Isn't that a leak?
A: It's a publishable key by design and grants nothing without RLS-passing credentials. The keys that must stay secret - Gemini and Pinecone - are backend-only.

Q: 74. How do you validate uploads?
A: Auth first, then filename sanitisation, an extension allow-list, an incremental read capped at 25 MB, and a non-empty check.

Q: 75. Why sanitise the filename if you never write to disk?
A: Because it's stored in vector metadata, echoed to every client, and used as a search filter. Path traversal and control characters get stripped.

Q: 76. What about prompt injection?
A: Mitigated by instructions in three prompts, which is the weakest category of defence. What limits it is that the model has no tools and no privileged actions, and isolation is enforced at the query level before the model runs - so injection can corrupt an answer but can't cross a tenant boundary.

Q: 77. What's your CORS configuration?
A: An explicit origin allow-list from an environment variable, with restricted methods and headers. It was previously a wildcard with credentials enabled, which is actually invalid per the spec.

Q: 78. What security feature is missing?
A: Rate limiting, first and foremost. Also no audit log, no sandboxed parsing, and no malware scanning beyond extension and size.

## Frontend (79-88)

Q: 79. Why React with no state library?
A: Four custom hooks own all state and components are presentational. For two views with one level of prop drilling, Redux or Context would be ceremony without benefit.

Q: 80. How do your hooks divide responsibility?
A: useAuth owns the session, useDocuments owns the library and uploads, useChat owns sessions and the SSE stream, useAudio owns TTS and speech recognition.

Q: 81. How do you avoid race conditions when the user changes?
A: A `cancelled` flag in each load effect's cleanup so a slow earlier request can't overwrite newer state, plus an AbortController that cancels any in-flight stream.

Q: 82. Why capture the session id when sending a message?
A: So tokens land in the conversation that asked the question even if the user switches tabs mid-stream.

Q: 83. How do optimistic updates work in delete?
A: Remove the card immediately, keep the previous list, and restore it if either the HTTP call or the Postgres delete fails. Hiding a document whose vectors are still searchable would be misleading.

Q: 84. Why is guest persistence skipped during streaming?
A: `chatSessions` changes on every token, so it would serialise the whole history to localStorage hundreds of times per answer.

Q: 85. How do citations render?
A: A regex finds `[n]` in the answer and swaps in a button that scrolls to the matching source card. Out-of-range numbers render as plain text.
FU: Why only on the latest message?

Q: 86. Why does only the newest answer have clickable citations?
A: Because sources are stored per session, not per message - the list only holds the most recent retrieval, so older messages were linking to the wrong chunks. That was a real bug.

Q: 87. How does the frontend know the backend URL?
A: `config.ts` reads `VITE_BACKEND_URL` and prefixes `https://` if there's no scheme, because Render injects a bare hostname.

Q: 88. What's the weakness of your message rendering?
A: It's a hand-rolled mini-renderer - no tables, code blocks or links - even though the prompt asks the model for tables. A full Markdown parser would fix it but complicates injecting citation chips.

## Operations and scale (89-100)

Q: 89. How is it deployed?
A: Two Render services from one `render.yaml` - a FastAPI web service with a health check, and a static site with an SPA rewrite.

Q: 90. What does your CI do?
A: flake8 for real bug classes, an app-import check, 70 pytest tests, then a TypeScript check and a production build. The deploy step only runs if both jobs pass on main.

Q: 91. Did your CI ever fail for an interesting reason?
A: Yes - `ModuleNotFoundError: No module named 'app'`. The `pytest` console script doesn't add the working directory to `sys.path`, unlike `python -m pytest`. Fixed at the root with `pythonpath = .` in pytest.ini rather than changing the CI command.

Q: 92. How are secrets managed?
A: Never in the repo. `render.yaml` marks them `sync: false` so values live in the dashboard; CI uses obvious placeholders; `.env` is gitignored with `.env.example` committed.

Q: 93. Build-time vs runtime environment variables?
A: `VITE_*` are substituted into the bundle at build time, so they need a rebuild and are public. Backend variables are read at process start and stay secret.

Q: 94. What happens at 1,000 users?
A: Rate limiting becomes mandatory, ingestion needs a queue, and I'd want 2-3 replicas plus Redis for shared caching. Gemini quota is the binding constraint.

Q: 95. What's your biggest bottleneck?
A: Cost and Gemini quota - up to five calls per query with no cap. Pinecone is the component I worry about least.

Q: 96. How would you reduce latency?
A: Measure first. Then: replace the LLM reranker with a local cross-encoder, make HyDE conditional, and run classification and embedding concurrently instead of sequentially.

Q: 97. How would you reduce cost?
A: Cache retrieval results per user and query, gate the vision pass to pages with a sparse text layer, make HyDE conditional, and use a cheaper model for classification.

Q: 98. What caches exist?
A: A bounded 256-entry LRU for query embeddings, an on-disk MD5-keyed TTS cache, and PyJWT's JWKS key cache. No Redis.
FU: What would you cache next?

Q: 99. What happens if Gemini or Pinecone goes down?
A: Gemini down: retrieval and generation fail, the user gets an error token and a complete-with-error event; uploads roll back and return 502. Pinecone down: startup fails, or at query time retrieval is caught and the answer is generated ungrounded with an honest prompt.

Q: 100. If you had two more weeks, what would you build?
A: In order: rate limiting, because it's the real risk. Then an evaluation harness, so I can measure retrieval instead of guessing. Then asynchronous ingestion so large PDFs actually work. Those three turn it from a good demo into something you could put real users on.
'''


HOW_TO_STUDY = r'''
# How to Study This Handbook

Five days, roughly two hours a day. Do not read it front to back in one sitting - the
question banks only stick after you understand the pipeline.

## Day 1 - Understand what you built (Parts 1, 2, 5)

**Goal:** be able to explain the project to a non-technical friend, then to an engineer.

1. Read **Part 5** first, even though it's the fifth chapter. If any term in it is unfamiliar,
   you are not ready for the rest.
2. Read **Part 1**. Say the 30-second and 1-minute versions out loud, from memory, three
   times. Record yourself once and listen back.
3. Read **Part 2**. Do not memorise the words - memorise the *order of ideas* in each answer.

**End-of-day test:** explain RAG, embeddings and cosine similarity to someone with no
technical background, using only analogies.

## Day 2 - Trace the data (Parts 3, 4, 27)

**Goal:** narrate what happens between a click and a rendered answer.

1. Read **Part 3**, then close it and draw the architecture from memory. Compare. Repeat
   until you can draw it in under three minutes.
2. Read **Part 4** slowly. Flows D and E are the two that matter most.
3. Skim **Part 27**, then open the actual repository and click through the files it lists.
   Match each file to its role.

**End-of-day test:** with the repo closed, narrate the upload flow and the query flow end to
end, naming the file responsible for each stage.

## Day 3 - The pipeline in depth (Parts 6-13)

**Goal:** defend every retrieval decision.

1. Read Parts **6, 7, 8** (ingestion, embeddings, HyDE).
2. Read Parts **9, 10** (Pinecone, routing).
3. Read Parts **11, 12, 13** (BM25, reranking, context expansion).
4. After each part, answer its interviewer questions **out loud without looking**.

**End-of-day test:** memorise the ten numbers from Part 40. Then explain, without notes, why
you retrieve 12 candidates, rerank 8 and use 4.

## Day 4 - Delivery and defence (Parts 14-20, 22, 28, 32, 33)

**Goal:** handle the harder questions and the honest ones.

1. Read Parts **15, 17, 18** (SSE, auth, security) - these get the most interview attention.
2. Skim Parts **14, 16, 19, 20** (prompts, citations, TTS, STT).
3. Read **Part 28** with the actual source files open beside it.
4. Read **Parts 32 and 33** carefully. Pick your three favourite trade-offs and your three
   most important limitations and be ready to raise them unprompted.

**End-of-day test:** explain the JWT algorithm-confusion defence, and explain why deletion
couldn't use a metadata filter. Those two answers demonstrate more than anything else in the
document.

## Day 5 - Interview simulation (Parts 29, 30, 31, 34-41)

**Goal:** perform.

1. Work through **Part 29** level by level. Mark every question you can't answer cleanly and
   go back to the relevant chapter.
2. Read **Part 30** as dialogue. The chains are how real interviews actually go - the third
   or fourth follow-up is where people fall apart.
3. Read **Part 31** and **Part 34**.
4. Rehearse the **Part 37** demo script with the app actually running. Twice.
5. Practise the **Part 38** whiteboard until it takes under three minutes.
6. Read **Part 41** last, as a final pass.

**End-of-day test:** have someone ask you twenty random questions from Part 41. Any answer
that takes more than fifteen seconds to start needs more work.

## The night before

Read only **Part 40** - the revision sheet - plus the five sentences at its end and your
chosen resume bullets from Part 39. Nothing else. Sleep matters more than one more chapter.

## Three habits that matter more than memorising

1. **Say "I don't know" cleanly when you don't.** Then say what you'd do to find out. This
   scores far better than a confident wrong answer, and interviewers are specifically probing
   for it.
2. **Volunteer a limitation with every strength.** "I used an LLM reranker because it was
   zero infrastructure, but it's the slowest stage in my pipeline" is the shape of an answer
   that sounds like an engineer.
3. **Never quote a number you can't defend.** If you say a percentage, expect "how did you
   measure that?" There are no benchmarks in this repository, so there are no percentages in
   this handbook.
'''
