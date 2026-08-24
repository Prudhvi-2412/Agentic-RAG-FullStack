PART_1 = r'''
# Part 1 - Project Overview

## Read this first

This handbook describes **DocuMind AI**, the project in the repository
`Prudhvi-2412/Agentic-RAG-FullStack`. Every statement here was written by reading the
**actual final source code**, not the README. Where the README and the code disagree, this
document says so explicitly and describes what the code really does.

The document assumes you know nothing about AI, RAG, vector databases, FastAPI, or
embeddings. Concepts are introduced from first principles, then connected to the exact lines
of your project that implement them.

## What is this project, in one sentence?

DocuMind AI is a web application where a signed-in user uploads their own documents
(PDF, Word, Markdown, plain text), and can then have a conversation with an AI assistant
that answers questions **using the contents of those documents**, showing exactly which
page of which file each part of the answer came from.

## What problem does it solve?

Imagine you have a 300-page book, a company policy manual, or a stack of research papers.
You want to ask: *"What does this say about longevity?"* You have three bad options today:

- **Read the whole thing.** Accurate but extremely slow.
- **Use Ctrl+F.** Fast, but it only finds the exact word you typed. If the book says
  "living a long life" and you searched "longevity", you find nothing.
- **Paste it into a general chatbot.** Large documents get truncated, the model may invent
  facts, and it usually cannot tell you which page an answer came from.

DocuMind AI solves this by combining search and generation. It first **finds** the handful
of passages in your documents that are actually relevant to your question, then asks a
language model to **answer using only those passages**, and finally shows you those passages
as clickable citations so you can verify the answer yourself.

## Why was this project built?

Three honest reasons, all defensible in an interview:

1. **To learn how production RAG systems actually work.** Not a tutorial notebook - a real
   full-stack application with authentication, multi-tenant data isolation, streaming,
   deployment and CI.
2. **Because a naive RAG demo is easy and a correct one is not.** The interesting engineering
   is in the parts tutorials skip: making sure user A cannot read user B's documents, making
   deletion actually work, handling API failures, and streaming tokens without blocking the
   server.
3. **To produce something demonstrable.** It is deployed, it has a live URL, and a
   non-technical person can use it in thirty seconds.

## Who would use it?

- A student querying textbooks and lecture notes.
- A professional searching internal policy documents or contracts.
- A researcher asking questions across a set of papers.
- Anyone who needs an answer *with a citation*, not just a confident-sounding paragraph.

## What makes it different from a normal chatbot?

| Aspect | Normal chatbot | DocuMind AI |
|---|---|---|
| Knowledge source | Whatever was in its training data | Your uploaded documents, retrieved at query time |
| Freshness | Frozen at training cutoff | Whatever you uploaded a minute ago |
| Citations | Usually none, or invented | Real filename + page number + the exact text snippet |
| Document size | Limited by the context window | Unlimited; only the relevant chunks are sent |
| Privacy | Files may be retained by the provider | Vectors are tagged with your user id; every search is filtered to you |
| Cost per query | Sends everything every time | Sends ~4 small passages, and skips retrieval entirely for chit-chat |

KEY: The single most important difference: a normal chatbot *remembers*; a RAG system *looks things up*. Looking things up is what makes citations possible.

## What does "RAG" mean?

**RAG = Retrieval-Augmented Generation.** Three words, three ideas:

- **Retrieval** - search a knowledge store and pull out the most relevant pieces of text.
- **Augmented** - take those pieces and paste them into the prompt you send to the AI.
- **Generation** - the AI writes an answer, grounded in the text you just gave it.

A one-line analogy: an **open-book exam**. A plain LLM is a student answering from memory,
and if they do not remember they guess confidently. RAG is the same student, but you hand
them the three most relevant pages of the textbook first and say "answer only from these".

## What does "Agentic" mean in THIS project?

Be precise and honest here, because interviewers probe this word.

In this project, "agentic" means exactly one thing: **before doing any work, an LLM decides
which pipeline the query should take.** A small Gemini call classifies every incoming
question into one of two routes:

- `DOCUMENT_QUERY` - the user is asking about their documents. Run the full retrieval
  pipeline (embed, search Pinecone, BM25, rerank, expand, then generate).
- `GENERAL_CHAT` - the user said "hello" or asked "what is FastAPI?". Skip retrieval
  entirely and answer directly.

There is a second, smaller agentic behaviour: **query condensation**. If the query is a
document query *and* there is prior conversation history, another LLM call rewrites
"and what about the second one?" into a standalone question like "what is the second
principle of ikigai?" before it is used for search.

KEY: Say this out loud in an interview: "It is agentic in the sense that an LLM makes a routing decision and rewrites the query - it is *not* a multi-step autonomous agent with tools, memory and a planning loop. I would not oversell it." Interviewers respect the distinction far more than the buzzword.

## What does "multimodal" mean in THIS project?

Multimodal means the ingestion pipeline processes **more than just text**. When a PDF is
uploaded, each page is handled two ways:

1. **PyMuPDF** extracts the page's embedded text layer - fast, exact, free.
2. **Gemini 2.5 Flash Vision** receives the same page rendered as a 150 DPI PNG image and
   is asked to describe everything visual: transcribe tables into Markdown, describe charts
   and diagrams, and note headers, signatures or handwriting.

Both outputs are concatenated, so a chart that contains no text at all still becomes
searchable text in the index. This is what lets the system answer questions about a table
or a diagram.

> Precision note: this is not strictly OCR. On a normal digital PDF, PyMuPDF already has the text and Gemini adds *layout and visual* understanding. On a scanned page with no text layer, Gemini Vision is effectively doing OCR. Both cases are handled by the same code path.

## What happens when a user interacts with it? (bird's-eye view)

~~~
   UPLOAD                                       ASK A QUESTION
   ------                                       --------------
   PDF/DOCX/TXT/MD                              "What is ikigai?"
        |                                              |
   parse text + vision                          LLM router decides:
        |                                       GENERAL_CHAT or DOCUMENT_QUERY
   split into ~750-char chunks                         |
        |                                       embed question (+HyDE)
   turn each chunk into 768 numbers                    |
        |                                       search Pinecone (filtered to YOU)
   store in Pinecone with your user id                 |
        |                                       BM25 + rerank + expand
   done - document is searchable                       |
                                                paste top 4 passages into prompt
                                                        |
                                                Gemini streams the answer word by word
                                                        |
                                                answer + citations appear live
~~~

## The four canned explanations

Memorise these. They are the four lengths an interviewer might want.

### The 30-second version

> "DocuMind AI is a full-stack RAG application. You sign in, upload your PDFs or Word
> documents, and then chat with them. The backend splits each document into chunks,
> converts them into vectors with Google's embedding model, and stores them in Pinecone
> tagged with your user id. When you ask a question, an LLM first decides whether it even
> needs your documents; if it does, it does a hybrid semantic-plus-keyword search, reranks
> the results with Gemini, and streams back an answer with page-level citations. It's React
> and TypeScript on the front, FastAPI on the back, with Supabase for auth, and it's
> deployed on Render with GitHub Actions CI."

### The 1-minute version

Everything above, plus:

> "The part I'm most pleased with is the multi-tenant isolation. Every vector in Pinecone
> carries a `user_id` in its metadata, and every single search applies an ownership filter
> before anything else - a signed-in user sees their own documents plus one shared demo
> document, and an anonymous visitor sees only the demo. The backend verifies the Supabase
> JWT signature itself rather than trusting the frontend, so you can't forge a user id.
> Deletion works the same way: it checks ownership before removing anything."

### The 2-minute version

Everything above, plus the retrieval detail:

> "Retrieval isn't just a single vector lookup. When a document query comes in, I first
> condense it against the chat history so follow-up questions like 'and the second one?'
> become standalone. Then I use HyDE - I ask Gemini to write a hypothetical answer to the
> question, embed both the real question and that hypothetical answer, and average the two
> vectors. That helps because a question and its answer are worded very differently, and
> answers look more like the document passages I'm searching for.
>
> That fused vector goes to Pinecone, which returns twelve candidates - three times what I
> actually need. I score those twelve with BM25, which is classic keyword scoring, normalise
> it, and blend it fifty-fifty with the cosine similarity. That catches exact terms like
> product codes that pure semantic search misses. Then the top eight go to Gemini as a
> cross-encoder-style reranker, which picks the best four. Finally I expand each of those
> four with its neighbouring chunks, because a 750-character chunk often cuts a sentence in
> half. Those four expanded passages go into the prompt, and the answer streams back over
> Server-Sent Events."

### The 5-minute version

Use the 2-minute version, then add these four blocks, roughly a minute each:

**Ingestion.** "Upload is authenticated - you cannot index a document anonymously, because
an indexed document needs an owner or I couldn't scope it later. I sanitise the filename,
cap the upload at 25 MB, and then parse. For a PDF, I render pages in batches of eight and
send each page image to Gemini Vision in parallel while extracting the text layer with
PyMuPDF. I deliberately render serially and only parallelise the API calls, because PyMuPDF
Document objects are not thread-safe - that was an actual bug I fixed. Then I clean the
text, split it with a recursive character splitter at 750 characters with 150 overlap,
embed in batches of 64, and upsert to Pinecone."

**Streaming.** "The answer streams over SSE, which is one-directional server-to-client
push over plain HTTP. I chose it over WebSockets because I only need one direction and I
didn't want a second protocol. The tricky part is that the Gemini SDK's streaming iterator
is blocking, so naively iterating it inside an async endpoint would freeze the entire event
loop for every other user. I run the producer on a worker thread and hand chunks back to
the event loop through an asyncio queue, with a stop flag so that if the client disconnects
the worker abandons the upstream stream instead of burning tokens."

**Failure handling.** "Every external call can fail, so there's a layered fallback. Gemini
rate limits get exponential backoff. If HyDE generation fails, retrieval continues with the
plain query embedding. If the reranker returns malformed JSON, I fall back to the hybrid
score ordering. If retrieval itself fails, I still emit an empty sources event so the
frontend knows the step finished rather than hanging. And if the JWKS endpoint is
unreachable I return 503, not 401, because a valid token shouldn't be reported as 'please
sign in again'."

**Operations.** "It's deployed on Render as two services from a render.yaml blueprint -
a FastAPI web service and a static React site. GitHub Actions runs flake8, an import check,
a 70-test pytest suite covering auth, tenant isolation, parsing and the SSE contract, plus
a TypeScript type-check and production build. Configuration fails fast: if a critical
environment variable is missing, the app refuses to start with a message naming the exact
variable, rather than booting with placeholder credentials."
'''


PART_2 = r'''
# Part 2 - How to Explain This Project in an Interview

This part gives you words to actually say. They are written to sound like a competent
student who built the thing, not like a press release. Read them aloud a few times; do not
memorise them word for word, memorise the *order of ideas*.

## "Tell me about your project."

> "It's called DocuMind AI. It's a full-stack Retrieval-Augmented Generation app - you sign
> in, upload documents like PDFs or Word files, and then ask questions about them in a chat
> interface, and it answers using the actual content of your documents with citations back
> to the specific page.
>
> The frontend is React 18 with TypeScript and Vite. The backend is FastAPI. Supabase
> handles authentication and stores chat history and the document list. Google Gemini does
> three jobs - vision parsing during upload, query routing, and answer generation - and
> Pinecone stores the vectors.
>
> The interesting engineering, I think, is in three places. First, retrieval isn't a naive
> single lookup - it's HyDE query expansion, then hybrid dense-plus-BM25 scoring, then an
> LLM reranker, then context expansion. Second, multi-tenant isolation - every vector is
> tagged with the owner's user id and every query is filtered by it, with the JWT verified
> server-side. Third, the streaming - tokens come back over Server-Sent Events without
> blocking the async event loop.
>
> It's deployed on Render with a GitHub Actions pipeline that runs a 70-test backend suite
> and the frontend build."

That is about 60 seconds. Stop there and let them pick a thread.

## "Explain the architecture."

Draw while you talk (see Part 38 for the exact whiteboard sequence). Say:

> "There are three tiers plus three external services.
>
> The browser runs React. It talks to Supabase directly for two things - signing in, and
> reading and writing chat history and the document list. It talks to my FastAPI backend
> for everything that needs a secret key: uploading, querying, and text-to-speech.
>
> FastAPI is organised in four layers - routes, models, services and core. Routes are thin;
> they do validation and authentication and then delegate. Services hold the actual logic:
> a document processor, an embedding service, a vector store service, a query router, a
> reranker, a chat service and a TTS service. Core holds config, auth, logging and retry.
> All the services are instantiated once at startup in a FastAPI lifespan handler and
> stashed on `app.state`, so I'm not rebuilding API clients on every request.
>
> The two external data systems are Pinecone, which holds the document vectors, and
> Supabase Postgres, which holds users, chat sessions and messages. Gemini is called for
> vision, routing, embeddings, reranking and generation.
>
> There are two flows worth separating: ingestion, which is write-heavy and slow, and query,
> which is read-heavy and needs to feel instant. That's why the answer streams."

## "Why did you build this?"

> "Two reasons. The practical one is that I kept hitting the limit of pasting documents into
> a chatbot - big files get truncated and I couldn't verify where an answer came from.
>
> The learning reason is more honest: I wanted to build a RAG system that wasn't a notebook
> demo. Anyone can do embed-search-generate in fifty lines. What I wanted to learn was the
> stuff around it - how do you stop one user reading another user's documents, what happens
> when the LLM API rate-limits you mid-request, how do you delete a document from a vector
> database that doesn't support delete-by-filter, how do you stream without blocking your
> server. Most of my time went into those problems, not into the RAG itself."

## "What was your contribution?"

Be specific and concrete. Vague ownership claims are the fastest way to lose credibility.

> "I built the whole thing - frontend, backend and deployment. But the parts I'd point at
> specifically:
>
> - The retrieval pipeline: HyDE fusion, the BM25 implementation, the hybrid scoring, the
>   Gemini reranker and the sentence-window context expansion.
> - The security model: server-side JWT verification supporting both Supabase signing modes,
>   the ownership filter that every Pinecone query passes through, and ownership-checked
>   deletion.
> - The streaming layer: the SSE event contract and the threaded producer that keeps the
>   async event loop free.
> - The test suite: 70 tests covering auth rejection cases, cross-tenant isolation, document
>   parsing edge cases and the exact SSE event ordering."

## "What was the hardest part?"

Pick a real one with a specific technical shape. This is the strongest one in the project:

> "Document deletion. It looked trivial - Pinecone's SDK has `index.delete(filter=...)`, so
> I wrote `delete(filter={'document_id': {'$eq': doc_id}})` and it returned without error.
> But deletes were silently not happening.
>
> The cause is that **serverless Pinecone indexes don't support delete-by-metadata-filter**.
> It's a documented limitation of the serverless tier, and the client-side call doesn't
> complain - the failure surfaces at the API, and my frontend wasn't checking the response
> status, so nothing bubbled up. Users deleted documents, the row disappeared from their
> list, and the vectors stayed in the index and kept showing up in search results.
>
> The fix was to change the deletion strategy: because my chunk IDs are structured as
> `{document_id}_p{page}_c{n}`, I can enumerate every vector for a document with
> `index.list(prefix=f'{document_id}_')` and then delete by explicit IDs in batches. And
> because I have to touch the vectors anyway, I fetch the first one and verify its
> `user_id` matches the caller before deleting anything - so ownership is enforced at the
> same time. I also made the frontend check `response.ok` and roll back its optimistic
> removal if the delete failed."

## "What technical challenge did you face?"

Have a second one ready so you're not repeating yourself:

> "Blocking calls inside async code. FastAPI endpoints are `async def`, which means they all
> share one event loop thread. My first version called the Pinecone SDK and the Gemini SDK
> directly inside those async functions - but those are synchronous, blocking HTTP clients.
> So while one user's embedding call was in flight, *every other request on the server was
> frozen*, including other people's streams.
>
> It's an easy mistake because it works perfectly with one user and falls apart with ten.
> The fix was `asyncio.to_thread` around every blocking SDK call, and for the streaming
> path something more involved: the Gemini streaming response is a blocking generator, so I
> run it on a dedicated worker thread that pushes chunks into an `asyncio.Queue` via
> `loop.call_soon_threadsafe`, and the async generator awaits that queue. There's a
> `threading.Event` stop flag so that when a client disconnects, the worker stops pulling
> from Gemini instead of generating tokens nobody will read."

## "How does your RAG pipeline work?"

Walk it in order, naming the reason for each stage:

> "Seven stages.
>
> **One, routing.** An LLM classifies the query as GENERAL_CHAT or DOCUMENT_QUERY. Chit-chat
> skips the whole pipeline.
>
> **Two, condensation.** If it's a document query and there's history, an LLM rewrites the
> question to be standalone, so pronouns and references resolve.
>
> **Three, HyDE embedding.** I embed the question, then ask Gemini to write a hypothetical
> answer, embed that too, and average the two vectors 50/50. Questions and answers are
> worded differently; the hypothetical answer looks more like the passages I'm searching.
>
> **Four, vector search.** That vector goes to Pinecone with `top_k=12` - three times what
> I need - always with an ownership filter applied.
>
> **Five, hybrid scoring.** I compute BM25 keyword scores over those twelve candidates
> locally, min-max normalise them, and blend 0.5 cosine + 0.5 BM25. Semantic search alone
> misses exact tokens like error codes or names.
>
> **Six, reranking.** The top eight go to Gemini in JSON mode with the question, and it
> returns the IDs of the best four in order. This is the most expensive stage but it's
> comparing the query against each passage directly, which a vector distance can't do.
>
> **Seven, context expansion.** For each of the final four, I fetch its neighbouring chunks
> by ID and stitch previous + current + next together, because a 750-character chunk often
> starts or ends mid-sentence.
>
> Then those four passages go into a grounding prompt that tells the model to answer only
> from the context and cite sources as [1], [2], and the answer streams back."

## "How is your project different from ChatGPT file upload?"

Answer fairly - do not pretend you beat a frontier product.

> "Honestly, for a single small file, ChatGPT's file upload is better - the model is
> stronger and it's less work.
>
> The differences that matter are architectural. First, **scale**: my index isn't bounded by
> a context window, so a user can have a hundred documents and each query still only sends
> four passages. Second, **verifiable citations**: I return the filename, page number and the
> exact snippet, and those come from my retrieval metadata, not from the model - so the
> model can't invent a page number. Third, **it's my data plane**: documents live in my
> Pinecone index scoped to my users, not a third party's account. Fourth, **routing**:
> I don't pay for a vector search when someone says hello.
>
> The thing I'd concede is answer quality on reasoning-heavy questions - I'm using
> Gemini 2.5 Flash, which is chosen for speed and cost, and retrieval can miss. If retrieval
> misses, my answer is worse than just handing the whole document to a big model."

KEY: That last paragraph - volunteering a real weakness - is usually what separates a candidate who built something from one who memorised a description of it.
'''
