"""Assembles the DocuMind AI interview handbook PDF from the content modules."""

import importlib
import sys

import render

MODULES = [
    "c01_overview",      # Parts 1-2
    "c02_architecture",  # Parts 3-4
    "c03_rag_zero",      # Part 5
    "c04_pipeline",      # Parts 6-10
    "c05_ranking",       # Parts 11-13
    "c06_delivery",      # Parts 14-20
    "c07_code",          # Parts 21-26
    "c08_walkthrough",   # Parts 27-28
    "c09_questions",     # Parts 29-31
    "c10_analysis",      # Parts 32-35
    "c11_practical",     # Parts 36-40
    "c12_top100",        # Part 41 + study roadmap
]

TITLE = "DocuMind AI"
SUBTITLE = [
    "The Complete Agentic RAG Project Handbook",
    "",
    "An interview preparation guide for",
    "github.com/Prudhvi-2412/Agentic-RAG-FullStack",
]

INTRO = r'''
# How to Use This Handbook

This document was written by reading the **actual final source code** of the repository -
not the README, and not generic RAG material. Where the README and the code disagreed, the
code won, and the disagreement is called out explicitly in the text.

## What each part is for

| Parts | Use them for |
|---|---|
| 1-2 | Explaining the project out loud, at four different lengths |
| 3-4 | Understanding and narrating the end-to-end data flow |
| 5 | Learning RAG from zero, if any term is unfamiliar |
| 6-13 | Defending every retrieval decision in depth |
| 14-20 | Prompts, streaming, citations, auth, security, voice |
| 21-28 | The code itself: frontend, backend, data, CI, walkthroughs |
| 29-31 | 140+ interview questions and follow-up chains |
| 32-35 | Trade-offs, limitations, scaling, failure modes |
| 36-41 | Debugging, demo script, whiteboard, CV material, top 100 |

## Conventions used

Blue boxes are clarifications and caveats. Yellow boxes marked **Interview key point** are
the sentences most worth memorising - there are roughly thirty of them across the document.
`Q.` / answer / *Likely follow-up* blocks are practice material; read the answers aloud.

## Three rules this handbook follows

1. **No invented numbers.** There is no benchmark in the repository, so there are no
   performance percentages here. If you want a metric on your CV, measure one first.
2. **Limitations are stated, not hidden.** Part 33 lists twenty real ones. Volunteering a
   weakness is what makes the strengths believable.
3. **Nothing is claimed that the code does not do.** Where a feature is partial - DOCX
   tables, Markdown rendering, page-boundary context expansion - it says so.

> A quick orientation before you start: the project is a multi-tenant RAG application. Users sign in with Supabase, upload documents that are parsed with PyMuPDF and Gemini Vision, chunked, embedded and stored in Pinecone tagged with their user id. Questions are routed by an LLM, retrieved through a HyDE + hybrid + rerank + expand pipeline scoped to that user, and answered by Gemini over an SSE stream with page-level citations.
'''


def main() -> int:
    sections = []
    for module_name in MODULES:
        module = importlib.import_module(module_name)
        parts = sorted(
            (n for n in dir(module) if n.startswith("PART_")),
            key=lambda n: int(n.split("_")[1]),
        )
        for name in parts:
            sections.append(getattr(module, name))
        # The study roadmap lives alongside Part 41 and must come last.
        if hasattr(module, "HOW_TO_STUDY"):
            sections.append(module.HOW_TO_STUDY)

    out = sys.argv[1] if len(sys.argv) > 1 else "DocuMind_AI_Interview_Handbook.pdf"
    render.build(out, TITLE, SUBTITLE, sections, intro_after_toc=INTRO)
    print(f"Wrote {out} from {len(sections)} sections")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
