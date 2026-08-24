PART_5 = r'''
# Part 5 - RAG From Absolute Zero

This part assumes you have never touched machine learning. Every concept follows the same
shape: simple definition, analogy, why this project needs it, how this project does it.

## LLM (Large Language Model)

**Simple definition.** A program that predicts the next word, over and over, until it has
written a whole answer. It learned to do this by reading an enormous amount of text.

**Analogy.** Someone who has read most of the internet and has a very good sense of "what
word usually comes next". Ask them a question and they produce a fluent, plausible reply -
but they are reciting patterns, not looking anything up.

**In this project.** Google **Gemini 2.5 Flash** is the LLM, and it does five separate jobs:
vision parsing during upload, query classification, HyDE hypothetical answers, reranking,
and final answer generation.

## Hallucination

**Simple definition.** When the model states something false with complete confidence.

**Why it happens.** The model optimises for *plausible*, not for *true*. If it does not know
the answer, "I don't know" is a less likely continuation than a confident invented one.

**Analogy.** A student in a viva who did not read chapter 7 but answers anyway, fluently and
wrongly, because silence scores zero.

**In this project.** Three defences: (1) supply real passages so the model does not need to
invent; (2) instruct it explicitly to say the answer is not in the documents if the context
does not cover it; (3) show the user the source snippets so they can check.

KEY: RAG *reduces* hallucination. It does not eliminate it. Saying "eliminates" in an interview is an immediate red flag.

## Context and context window

**Context** = everything you send the model in one request: instructions, retrieved
passages, conversation history and the question.

**Context window** = the maximum size of that, measured in tokens. It is finite. This is
precisely why you cannot paste a 300-page book in - and precisely why RAG exists.

## Token

**Simple definition.** The unit the model actually reads. Roughly ¾ of a word in English.

- `"cat"` -> 1 token
- `"unbelievable"` -> maybe 3 (`un`, `believ`, `able`)
- 750 characters (this project's chunk size) -> roughly 190 tokens

**Why you care.** Billing and limits are per token. Four chunks of ~190 tokens is ~760
tokens of context - cheap. A whole book is ~150,000 tokens - expensive and often impossible.

## Prompt

**Simple definition.** The full text you send. In this project it is assembled in
`ChatService._build_prompt()` from four pieces: a role instruction, optional conversation
history, the retrieved context blocks, and the user's question - followed by grounding rules.

## Embedding

**Simple definition.** A list of numbers that represents the *meaning* of a piece of text.
Similar meanings produce similar lists.

**Analogy.** Think of a map of a country. Every town has a latitude and longitude - two
numbers. Towns that are close in reality are close on the map. An embedding is the same
idea with 768 numbers instead of 2, and "closeness" means "similar meaning" instead of
"physically near".

**Tiny example.** Imagine a toy 3-dimensional embedding where the axes are roughly
[royalty, gender, age]:

```
"king"   -> [0.95, 0.90, 0.60]
"queen"  -> [0.95, 0.10, 0.60]
"prince" -> [0.90, 0.88, 0.15]
"apple"  -> [0.02, 0.50, 0.30]
```

`king` and `queen` differ mainly in one dimension. `apple` is far from all three. Nobody
programmed those axes - the model learned them. Real embeddings have 768 dimensions and the
axes are not human-interpretable, but the principle is identical.

**In this project.** `gemini-embedding-001` with `output_dimensionality=768`.

## Vector

Just a fancy word for "a list of numbers". An embedding *is* a vector. `[0.12, -0.44, ...]`
with 768 entries.

## Vector database

**Simple definition.** A database built to answer "which stored vectors are closest to this
one?" quickly.

**Why a normal database fails.** In Postgres you can ask `WHERE name = 'ikigai'`. You cannot
efficiently ask "find the 12 rows whose 768-number list points in the most similar direction
to this list" - not without scanning every row and doing 768 multiplications each.

**Analogy.** A normal index is like a book's alphabetical index - exact lookups. A vector
index is like a librarian who knows which books are *about similar topics*, even with no
words in common.

**In this project.** Pinecone serverless: 768 dimensions, cosine metric, AWS `us-east-1`.

## Semantic search

**Simple definition.** Search by meaning rather than by exact characters.

**Example.** Query "how to live a long life". Keyword search finds nothing in a document
that says "longevity and Japanese diet". Semantic search finds it, because the two phrases
embed to nearby vectors.

## Retrieval and generation

- **Retrieval** = the search step. Find the most relevant passages. Cheap, fast, factual.
- **Generation** = the writing step. An LLM composes prose from those passages. Expensive,
  slower, fluent.

RAG is simply: retrieve, then generate.

## Chunking

**Simple definition.** Cutting a document into small pieces before embedding it.

**Why.** One vector can only represent so much. Embed a whole book and you get the "average
meaning of a book", which matches every query equally badly. Embed 800 chunks and each one
represents one specific idea. Chunking is also what makes page-level citation possible.

**In this project.** `RecursiveCharacterTextSplitter(chunk_size=750, chunk_overlap=150)`.

## Metadata

**Simple definition.** Extra facts stored alongside each vector.

**In this project**, each vector carries:

| Field | Example | Used for |
|---|---|---|
| `document_id` | `a3f1...` (UUID) | grouping, deletion |
| `filename` | `Ikigai.pdf` | citation display, user filters |
| `chunk_id` | `a3f1..._p12_c2` | context expansion, DOM anchors |
| `page_number` | `12` | citation display |
| `upload_time` | ISO 8601 UTC | bookkeeping |
| `source_type` | `pdf` | bookkeeping |
| `user_id` | Supabase UUID | **the ownership filter** |
| `context` | the chunk's full text | returning the passage itself |

KEY: Storing the chunk text in `metadata["context"]` means retrieval returns the passage directly. Without it you would need a second database round-trip to turn IDs into text.

## Similarity and cosine similarity

**The question.** Given two vectors, how similar are they?

**Cosine similarity** measures the **angle** between them, ignoring length:

- `1.0` - identical direction (same meaning)
- `0.0` - perpendicular (unrelated)
- `-1.0` - opposite direction

**Analogy.** Two people pointing at the horizon. Cosine similarity asks whether they are
pointing the same way. It does not care whether one has longer arms - only direction.

**Why ignore length?** In text embeddings, magnitude tends to track things like document
length, not meaning. A one-line summary and a three-paragraph explanation of the same idea
should count as similar.

**Formula** (you may be asked to write it):

```
cos(A, B) = (A · B) / (||A|| * ||B||)

A · B    = a1*b1 + a2*b2 + ... + a768*b768     (dot product)
||A||    = sqrt(a1^2 + a2^2 + ... + a768^2)    (length)
```

## Putting it together: three generations of chatbot

### 1. Traditional chatbot

~~~
   Question ------> [ LLM (frozen knowledge) ] ------> Answer
~~~

- Answers from training data only.
- Cannot know your documents, or anything after its cutoff.
- No citations. Hallucinates when unsure.

### 2. RAG chatbot

~~~
   Question --> embed --> [ Vector DB ] --> top passages
                                               |
                              Question + passages --> [ LLM ] --> Answer + citations
~~~

- Grounded in your data, current, citable.
- **But**: it retrieves for *every* query, including "hello". That is wasted latency and
  money, and forcing irrelevant context into a greeting can even make the answer worse.

### 3. Agentic RAG (this project)

~~~
                        +--> GENERAL_CHAT ---------------------> [ LLM ] --> Answer
                        |
   Question --> [ LLM router ]
                        |
                        +--> DOCUMENT_QUERY --> condense --> HyDE embed --> [ Vector DB ]
                                                                                 |
                                                                    12 candidates
                                                                                 |
                                                        BM25 + hybrid score --> top 8
                                                                                 |
                                                          [ LLM reranker ] --> top 4
                                                                                 |
                                                            context expansion (c-1,c,c+1)
                                                                                 |
                                                    Question + passages --> [ LLM ] --> Answer
                                                                                        + citations
~~~

The difference is that **a decision is made before the pipeline runs**, and the retrieval
pipeline itself has multiple refinement stages rather than one lookup.

## The end-to-end example you should be able to narrate

> User uploads `Ikigai.pdf` (200 pages).
>
> 1. PyMuPDF pulls the text of every page; Gemini Vision describes the diagrams.
> 2. Each page is cleaned and split into ~750-character chunks with 150 overlap - say 850
>    chunks total.
> 3. Each chunk becomes 768 numbers via `gemini-embedding-001` (batches of 64).
> 4. All 850 vectors are upserted to Pinecone, each tagged with the uploader's `user_id`.
>
> User asks: *"What does the book say about flow?"*
>
> 5. The router says `DOCUMENT_QUERY`.
> 6. The question is embedded; Gemini writes a hypothetical answer about flow states; that
>    is embedded too; the two vectors are averaged.
> 7. Pinecone returns the 12 nearest vectors **belonging to this user**.
> 8. BM25 boosts chunks literally containing "flow"; scores are blended 50/50.
> 9. Gemini reranks the top 8 and picks the best 4.
> 10. Each of the 4 is stitched together with its neighbouring chunks.
> 11. Those 4 passages plus the question go to Gemini with grounding instructions.
> 12. The answer streams back word by word with `[1]`-style citations, and the right-hand
>     panel shows `Ikigai.pdf, page 96, 87.4% match` with the actual snippet.
'''
