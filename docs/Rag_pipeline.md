# RAG Pipeline Documentation

This document details the Retrieval-Augmented Generation pipeline used in pali.canon.

## Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              OFFLINE (Indexing)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   PDFs ──▶ OCR Check ──▶ Text Extract ──▶ Chunking ──▶ Embedding ──▶ Store │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ ChromaDB
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ONLINE (Query)                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Question ──▶ Planning ──▶ Retrieval ──▶ Synthesis ──▶ Answer + Sources   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Stage 1: Ingestion

### 1.1 PDF Discovery

```python
# indexer.py: _iter_pdfs()
for dirpath, _, files in os.walk(data_dir):
    for f in files:
        if f.lower().endswith(".pdf"):
            yield os.path.join(dirpath, f)
```

All PDFs under the data directory are discovered recursively. No filtering by name or folder—everything gets indexed.

### 1.2 OCR Processing

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Source PDF │────▶│ _has_text()  │────▶│ Has text?   │
└─────────────┘     │ Check 3 pages│     └──────┬──────┘
                    └──────────────┘            │
                                    ┌──────────┴──────────┐
                                    │                     │
                                   YES                    NO
                                    │                     │
                                    ▼                     ▼
                            ┌─────────────┐       ┌─────────────┐
                            │ Copy to     │       │ Run OCRmyPDF│
                            │ OCR_CACHE   │       │ to OCR_CACHE│
                            └─────────────┘       └─────────────┘
```

**Key behaviors:**
- Text detection checks first 3 pages only (performance optimization)
- OCR'd files are cached in `data/ocr_cache/` mirroring source structure
- Subsequent runs skip OCR if cache exists

### 1.3 Text Extraction

```python
# PyMuPDF (fitz) extracts text per page
with fitz.open(pdf_path) as doc:
    for page_idx in range(len(doc)):
        text = doc[page_idx].get_text("text")
```

- Extraction is page-by-page
- Empty pages are skipped
- No cross-page merging (limitation)

---

## Stage 2: Chunking

### 2.1 Sentence Splitting

```python
_SPLIT_RE = re.compile(r"(?<=[\.!?])\s+(?=[A-ZĀĪŪṄÑṬḌḶ])")
```

Split on sentence-ending punctuation followed by whitespace and a capital letter (including Pāli diacriticals).

**Known limitations:**
- Breaks on abbreviations ("e.g. The...")
- Misses sentences starting with lowercase
- Doesn't handle verse numbers or lists

### 2.2 Chunk Assembly

```
Sentences: [s1, s2, s3, s4, s5, s6, s7, s8]

Chunk 1: [s1, s2, s3, s4] (800 chars)
Chunk 2: [s3, s4, s5, s6] (overlap from s3)
Chunk 3: [s5, s6, s7, s8] (overlap from s5)
```

**Parameters:**
- `SENT_LEN = 800` — Maximum characters per chunk
- `SENT_OVERLAP = 120` — Characters of overlap between chunks

The overlap ensures context continuity; a concept mentioned at the end of chunk 1 appears at the start of chunk 2.

### 2.3 Chunk Format

Each chunk becomes a `Document` with:

```python
Document(
    page_content="The actual text of the chunk...",
    metadata={
        "pdf_name": "majjhima_nikaya1.pdf",
        "page": 42,
        "span_id": "p42_c3",       # page 42, chunk 3
        "folder_path": "sutta_pitaka/majjhima_nikaya",
        "basket": "sutta",         # vinaya/sutta/abhidhamma
        "relpath": "sutta_pitaka/majjhima_nikaya/majjhima_nikaya1.pdf"
    }
)
```

**Missing metadata (opportunity for improvement):**
- Sutta number (MN 21)
- PTS reference (M i 126)
- Verse number (for verse texts)
- Translation/edition identifier

---

## Stage 3: Embedding

### 3.1 Model

```python
embeddings = OllamaEmbeddings(model="nomic-embed-text")
```

**nomic-embed-text specifications:**
- 768-dimensional vectors
- 8192 token context window
- Trained on general text (not Buddhist-specific)

### 3.2 Storage

```python
vectordb = Chroma(
    collection_name="pali_canon",
    embedding_function=embeddings,
    persist_directory="/path/to/chroma"
)
```

ChromaDB uses HNSW (Hierarchical Navigable Small World) indexing for approximate nearest neighbor search.

**Batch processing:**
- Documents are accumulated in memory
- Flushed to Chroma every 500 documents
- Prevents memory issues with large collections

---

## Stage 4: Query Planning

### 4.1 Citation Extraction

```python
ID_RE = re.compile(r"\b([DMAS]N)\s*[- ]?\s*(\d{1,3})(?:[\. ]\s*(\d{1,3}))?\b", re.I)
```

Matches patterns like:
- `SN 35.28` → `SN 35.28`
- `DN 22` → `DN 22`
- `MN 21` → `MN 21`
- `AN 4.159` → `AN 4.159`

### 4.2 Basket Detection

```python
def _basket_hint(q: str) -> Optional[str]:
    ql = q.lower()
    if "vinaya" in ql: return "vinaya"
    if "abhidhamma" in ql: return "abhidhamma"
    # ... sutta checks
```

Keyword-based detection of which piṭaka the user is asking about.

### 4.3 Alias Resolution

```python
# Uses RapidFuzz for fuzzy matching
matches = process.extract(q.lower(), ALIAS_KEYS, scorer=fuzz.WRatio, limit=5)
```

Maps nicknames to canonical IDs:
- "fire sermon" → `SN 35.28`
- "simile of the saw" → `MN 21`

**Requires:** `config/aliases.csv` file (not provided in current repo)

### 4.4 Plan Output

```python
{
    "targets": ["SN 35.28"],           # Explicit sutta references
    "basket_hint": "sutta",            # Which piṭaka
    "query_terms": [                   # Search terms
        "What is the Fire Sermon?",
        "SN 35.28"
    ]
}
```

---

## Stage 5: Retrieval

### 5.1 Query Construction

```python
q = " | ".join(queries)  # "What is the Fire Sermon? | SN 35.28"
```

Query terms are joined with `|` for semantic search.

### 5.2 MMR Search

```python
docs = db.max_marginal_relevance_search(q, k=8, fetch_k=32)
```

**Maximal Marginal Relevance:**
- Fetches 32 candidates by similarity
- Selects 8 that balance relevance and diversity
- Reduces redundant/repetitive results

### 5.3 Basket Bias

```python
def _score_bias(doc, basket_hint):
    if basket_hint and doc.metadata.get("basket") == basket_hint:
        return 0.10
    return 0.0
```

Documents matching the basket hint get a +0.10 bonus. This is a *soft* bias; it doesn't filter, only promotes.

### 5.4 Translation Deduplication

```python
def _dedupe_by_translation(docs):
    # Keep first by alphabetical pdf_name
    seen_names = set()
    for d in sorted(docs, key=lambda x: x.metadata.get("pdf_name").lower()):
        name = d.metadata.get("pdf_name").lower()
        if name in seen_names:
            continue
        seen_names.add(name)
        kept.append(d)
    return kept
```

Prevents retrieving the same passage from multiple translations (e.g., Bodhi and Ñāṇamoli versions).

### 5.5 Retrieval Output

```python
[
    {
        "text": "All the sense bases are burning...",
        "pdf_name": "samyutta_nikaya4.pdf",
        "page": 112,
        "span_id": "p112_c2",
        "relpath": "sutta_pitaka/samyutta_nikaya/samyutta_nikaya4.pdf",
        "score": 0.0  # Placeholder; MMR doesn't return scores
    },
    # ... more hits
]
```

---

## Stage 6: Synthesis

### 6.1 Context Formatting

```python
def _format_context(hits):
    lines = []
    for i, h in enumerate(hits, 1):
        header = f"[{i}] {h['relpath']} p.{h['page']}"
        body = h["text"].strip()
        lines.append(f"{header}\n{body}")
    return "\n\n".join(lines)
```

Output:
```
[1] sutta_pitaka/samyutta_nikaya/samyutta_nikaya4.pdf p.112
All the sense bases are burning...

[2] sutta_pitaka/samyutta_nikaya/samyutta_nikaya4.pdf p.113
Burning with what? Burning with the fire of passion...
```

### 6.2 System Prompt

```python
SYS = """You are a wise and compassionate scholar of the Pāli Canon. Your goal is 
to not just answer questions, but to provide insightful, reflective, and 
thought-provoking responses based on the provided passages.
- Freely quote from the text to illustrate your points.
- Connect concepts and ideas from different passages.
- Where appropriate, ask reflective questions.
- Always cite your sources in the format: 'folder/filename.pdf — p.<page>'.
- If the passages don't contain a clear answer, say so."""
```

### 6.3 Prompt Assembly

```python
prompt = f"{SYS}\n\nQuestion: {query}\n\nContext:\n{ctx}\n\nAnswer:"
```

The full prompt structure:
1. System instructions
2. User's question
3. Retrieved context (numbered)
4. "Answer:" marker for generation

### 6.4 LLM Generation

```python
llm = OllamaLLM(model="mistral")
answer = llm.invoke(prompt)
```

**Model:** Mistral 7B via Ollama
**Context:** ~4000 tokens available for context + generation

### 6.5 Source Formatting

```python
def _format_sources(hits):
    uniq = []
    for h in hits:
        sig = (h['relpath'], h['page'])
        if sig not in seen:
            uniq.append(f"{h['relpath']} — p.{h['page']}")
    return "Sources:\n" + "\n".join(f"- {s}" for s in uniq)
```

Output:
```
Sources:
- sutta_pitaka/samyutta_nikaya/samyutta_nikaya4.pdf — p.112
- sutta_pitaka/samyutta_nikaya/samyutta_nikaya4.pdf — p.113
```

---

## Metadata Schema

### Current Schema

| Field | Type | Source | Example |
|-------|------|--------|---------|
| `pdf_name` | string | Filename | `"majjhima_nikaya1.pdf"` |
| `page` | int | PyMuPDF | `42` |
| `span_id` | string | Generated | `"p42_c3"` |
| `folder_path` | string | Filesystem | `"sutta_pitaka/majjhima_nikaya"` |
| `basket` | string | Path-inferred | `"sutta"` |
| `relpath` | string | Constructed | `"sutta_pitaka/majjhima_nikaya/majjhima_nikaya1.pdf"` |

### Proposed Extended Schema

| Field | Type | Source | Example |
|-------|------|--------|---------|
| `sutta_id` | string | Extracted | `"MN 21"` |
| `pts_ref` | string | Extracted | `"M i 126"` |
| `verse_num` | int | Extracted | `15` |
| `nikaya` | string | Path-inferred | `"majjhima"` |
| `translation` | string | Filename | `"bodhi"` |
| `chunk_type` | string | Detected | `"prose" / "verse" / "list"` |

---

## Citation Preservation

### Where Citations Are Created

1. **Indexing:** `pdf_name` and `page` stored in metadata
2. **Retrieval:** `relpath` constructed from `folder_path` + `pdf_name`
3. **Synthesis:** Sources formatted as `relpath — p.page`

### Citation Flow

```
PDF: data/pali_canon/sutta_pitaka/majjhima_nikaya/majjhima_nikaya1.pdf
                                    │
                                    ▼
Indexed with: pdf_name="majjhima_nikaya1.pdf"
              folder_path="sutta_pitaka/majjhima_nikaya"
              page=42
                                    │
                                    ▼
Retrieved with: relpath="sutta_pitaka/majjhima_nikaya/majjhima_nikaya1.pdf"
                page=42
                                    │
                                    ▼
Displayed as: "sutta_pitaka/majjhima_nikaya/majjhima_nikaya1.pdf — p.42"
```

### Known Issues

1. **Page numbers are PDF pages, not canonical page numbers**
   - PDF page 42 might be book page 37 (accounting for front matter)
   - No mapping to PTS page numbers

2. **No sub-page precision**
   - Multiple chunks from same page show same citation
   - No way to point to specific paragraph

3. **Translation ambiguity**
   - If multiple translations indexed, citation doesn't clarify which
   - Deduplication may hide relevant alternative translations

---

## Suggested Chunk Format for Enhanced Citations

```python
Document(
    page_content="...",
    metadata={
        # Current
        "pdf_name": "majjhima_nikaya1.pdf",
        "page": 42,
        "span_id": "p42_c3",
        "folder_path": "sutta_pitaka/majjhima_nikaya",
        "basket": "sutta",
        "relpath": "sutta_pitaka/majjhima_nikaya/majjhima_nikaya1.pdf",
        
        # Proposed additions
        "sutta_id": "MN 21",              # Extracted from content
        "sutta_title": "Kakacūpama Sutta", # Extracted from content
        "pts_volume": "M",                 # Majjhima Nikāya
        "pts_page": "i 126",               # PTS reference
        "nikaya": "majjhima",              # Normalized nikāya name
        "translation": "Ñāṇamoli-Bodhi",   # Translator(s)
        "chunk_type": "prose",             # prose/verse/list/formula
        "char_offset": 12450,              # Position in PDF for precise lookup
    }
)
```

This would enable:
- Direct lookup by `sutta_id`
- Filtering by `nikaya`
- Translation-aware deduplication
- PTS reference in citations
