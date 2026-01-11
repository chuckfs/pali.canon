# Architecture

This document describes the current architecture of pali.canon and the proposed target architecture.

## Current Architecture (As-Built)

### Module Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                           app.py (UI Layer)                         │
│                    Gradio Web Interface                             │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│  planner.py   │       │ retriever.py  │       │synthesizer.py │
│               │       │               │       │               │
│ Query Analysis│──────▶│ Vector Search │──────▶│ LLM Response  │
│ Citation Parse│       │ MMR + Dedup   │       │ + Citations   │
└───────────────┘       └───────┬───────┘       └───────────────┘
                                │
                                ▼
                        ┌───────────────┐
                        │  ChromaDB     │
                        │  (persisted)  │
                        └───────┬───────┘
                                │
                                │ (built by)
                                ▼
                        ┌───────────────┐
                        │  indexer.py   │
                        │               │
                        │ PDF → OCR →   │
                        │ Chunk → Embed │
                        └───────────────┘
```

### Data Flow: Query to Answer

```
User Question
      │
      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 1. PLANNING (planner.py)                                            │
│                                                                     │
│    Input:  "What is the Fire Sermon (SN 35.28)?"                   │
│    Output: {                                                        │
│      "targets": ["SN 35.28"],                                      │
│      "basket_hint": "sutta",                                       │
│      "query_terms": ["What is the Fire Sermon...", "SN 35.28"]     │
│    }                                                                │
└─────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. RETRIEVAL (retriever.py)                                         │
│                                                                     │
│    - Joins query_terms with " | "                                  │
│    - Runs MMR search against ChromaDB (k=8, fetch_k=32)            │
│    - Applies +0.10 score bias for matching basket                  │
│    - Deduplicates by pdf_name (keeps alphabetically first)         │
│                                                                     │
│    Output: List of hit dicts with text, pdf_name, page, relpath    │
└─────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. SYNTHESIS (synthesizer.py)                                       │
│                                                                     │
│    - Formats hits as numbered context blocks                       │
│    - Constructs prompt: SYS + Question + Context                   │
│    - Calls Ollama (mistral) for completion                         │
│    - Appends deduplicated source list                              │
│                                                                     │
│    Output: Answer text with "Sources:" section                     │
└─────────────────────────────────────────────────────────────────────┘
      │
      ▼
User sees answer
```

### Indexing Pipeline

```
PDF Files (data/pali_canon/)
      │
      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 1. FILE DISCOVERY                                                   │
│    os.walk() finds all *.pdf files recursively                     │
└─────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. OCR CHECK                                                        │
│    - _has_text(): Check first 3 pages for text layer               │
│    - If text exists: copy to OCR_CACHE                             │
│    - If no text: run ocrmypdf → OCR_CACHE                          │
└─────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. TEXT EXTRACTION                                                  │
│    - PyMuPDF extracts text page-by-page                            │
│    - Empty pages skipped                                            │
└─────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4. CHUNKING                                                         │
│    - Sentence split: regex on [.!?] + capital letter               │
│    - Chunk assembly: 800 chars max, 120 char overlap               │
│    - Each chunk gets metadata:                                      │
│      {pdf_name, page, span_id, folder_path, basket, relpath}       │
└─────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 5. EMBEDDING + STORAGE                                              │
│    - OllamaEmbeddings(nomic-embed-text) generates vectors          │
│    - ChromaDB stores with auto-persist                             │
│    - Batch flush every 500 documents                               │
└─────────────────────────────────────────────────────────────────────┘
```

### Current Module Responsibilities

| Module | Responsibility | Dependencies |
|--------|----------------|--------------|
| `config.py` | Load env vars, expand paths, create dirs | python-dotenv |
| `indexer.py` | PDF→OCR→Chunk→Embed→Store | PyMuPDF, ocrmypdf, langchain-ollama, langchain-chroma |
| `planner.py` | Parse citations, detect basket, fuzzy match aliases | rapidfuzz |
| `retriever.py` | MMR search, basket bias, dedup | langchain-ollama, langchain-chroma |
| `synthesizer.py` | Format context, generate answer, list sources | langchain-ollama |
| `app.py` | Gradio UI, chat interface, workbook generator | gradio |
| `generate_full_workbook.py` | Batch generate 365 entries | planner, retriever, synthesizer |

---

## Target Architecture (Proposed)

### Directory Structure

```
pali.canon/
├── src/
│   ├── __init__.py
│   ├── config.py              # ALL configuration (consolidated)
│   │
│   ├── indexing/
│   │   ├── __init__.py
│   │   ├── indexer.py         # Orchestration
│   │   ├── ocr.py             # OCR handling (extracted)
│   │   ├── chunker.py         # Chunking strategies (pluggable)
│   │   └── metadata.py        # Citation/ref extraction
│   │
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── planner.py         # Query analysis
│   │   ├── retriever.py       # Vector + hybrid search
│   │   └── reranker.py        # Cross-encoder reranking
│   │
│   └── synthesis/
│       ├── __init__.py
│       ├── synthesizer.py     # Answer generation
│       ├── prompts.py         # System prompts (separate)
│       └── grounding.py       # Quote validation
│
├── ui/
│   ├── __init__.py
│   └── app.py                 # Gradio interface only
│
├── scripts/
│   ├── generate_workbook.py
│   ├── create_golden_set.py
│   └── run_eval.py
│
├── tests/
│   ├── test_planner.py
│   ├── test_retriever.py
│   └── test_synthesizer.py
│
├── eval/
│   ├── golden_set.json
│   └── results/
│
├── config/
│   └── aliases.csv
│
├── data/
│   ├── curriculum.json
│   └── pali_canon/
│
└── docs/
    ├── ARCHITECTURE.md
    ├── RAG_PIPELINE.md
    └── EVAL.md
```

### Proposed Data Flow with Enhancements

```
User Question
      │
      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 1. QUERY ANALYSIS (src/retrieval/planner.py)                        │
│                                                                     │
│    NEW: Query expansion for Pāli terms                             │
│    NEW: Intent classification (factual vs. reflective)             │
└─────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. HYBRID RETRIEVAL (src/retrieval/retriever.py)                    │
│                                                                     │
│    NEW: Semantic search + BM25 keyword search                      │
│    NEW: Metadata filtering (basket, nikāya)                        │
│    NEW: Configurable fusion strategy                               │
└─────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. RERANKING (src/retrieval/reranker.py)                           │
│                                                                     │
│    NEW: Cross-encoder scoring                                      │
│    NEW: Diversity enforcement                                      │
└─────────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4. GROUNDED SYNTHESIS (src/synthesis/synthesizer.py)               │
│                                                                     │
│    NEW: Confidence threshold check                                 │
│    NEW: Quote extraction validation                                │
│    NEW: Explicit refusal when low confidence                       │
└─────────────────────────────────────────────────────────────────────┘
      │
      ▼
User sees answer (or honest "I don't know")
```

### Key Architectural Changes

| Current | Proposed | Rationale |
|---------|----------|-----------|
| Flat file structure | `src/` package hierarchy | Testability, imports, maintainability |
| Config in multiple files | Single `config.py` with validation | Single source of truth |
| Semantic-only search | Hybrid semantic + BM25 | Better keyword matching for proper nouns |
| No reranking | Cross-encoder reranker | Higher precision in top results |
| Prompt-only grounding | Quote validation + confidence thresholds | Reduce hallucination |
| No evaluation | Golden set + automated metrics | Measurable quality |
| No tests | pytest suite | Regression prevention |

### Module Boundaries (Target)

**Core (src/):** The RAG pipeline. Should be importable as a library.
```python
from src.retrieval import plan, retrieve
from src.synthesis import synthesize
```

**Integration (ui/):** Framework-specific code. Gradio today, could be FastAPI tomorrow.

**Tooling (scripts/):** One-off batch jobs. Not imported by core.

**Quality (tests/, eval/):** Validation infrastructure. Not shipped to users.

---

## Key Tradeoffs

### 1. Local vs. Cloud

**Choice:** Fully local (Ollama)

**Tradeoff:**
- ✅ Complete privacy, no API costs, offline capable
- ❌ Limited model size, slower than cloud, no fine-tuning

### 2. Chunk Size

**Choice:** 800 characters with 120 overlap

**Tradeoff:**
- ✅ Precise retrieval, fits in context window
- ❌ May split coherent passages, loses document-level context

**Recommendation:** Experiment with 1500 chars; measure impact on retrieval quality.

### 3. MMR vs. Similarity Search

**Choice:** MMR with similarity fallback

**Tradeoff:**
- ✅ Diverse results, reduces redundancy
- ❌ Slightly slower, may sacrifice top relevance for diversity

### 4. Single Embedding Model vs. Domain-Specific

**Choice:** General-purpose `nomic-embed-text`

**Tradeoff:**
- ✅ No training required, good out-of-box performance
- ❌ May not capture Pāli-specific semantics

**Recommendation:** Long-term, consider fine-tuning on Buddhist text similarity pairs.

### 5. Flat Metadata vs. Structured Citations

**Choice:** Basic metadata (pdf_name, page, basket)

**Tradeoff:**
- ✅ Simple to implement, works for any PDF
- ❌ Can't retrieve by sutta number, no verse-level precision

**Recommendation:** Add structured citation extraction as a high-priority enhancement.
