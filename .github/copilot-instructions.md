# Copilot Instructions for pali.canon

## Project Overview

This is a Canon-grounded Q&A system for the Theravāda Pāli Canon with page-level citations. The pipeline follows a G-RAG-G architecture: planner → retriever → synthesizer, using Mistral via Ollama and Chroma for embeddings.

## Architecture

- **Planner** (`planner.py`): Parses user queries to extract IDs, resolve aliases, and infer constraints (basket/nikāya)
- **Retriever** (`retriever.py`): Two-phase retrieval with hybrid ranking (vector + BM25) using Chroma
- **Synthesizer** (`synthesizer.py`): Generates grounded answers with citations using Mistral via Ollama
- **Alias Loader** (`alias_loader.py`): Loads and fuzzy-matches sutta aliases from CSV/YAML
- **Indexers**: 
  - `index_canon.py`: Baseline indexer that extracts existing text from PDFs
  - `index_canon_ocr.py`: OCR-first indexer (recommended) that ensures all pages are searchable
- **CLI** (`grg_local.py`): Command-line interface for querying the Canon
- **Web UI** (`web/app.py`): Gradio-based web interface

## Code Style and Conventions

### Python Style
- Use UTF-8 encoding with `# -*- coding: utf-8 -*-` header
- Include descriptive module docstrings explaining purpose and key features
- Use type hints from `typing` module (e.g., `Dict[str, Any]`, `List[str]`)
- Use `from __future__ import annotations` for forward compatibility
- Follow PEP 8 naming conventions:
  - Functions and variables: `snake_case`
  - Constants: `UPPER_CASE`
  - Private/internal functions: prefix with `_`

### Pāli Text Handling
- Preserve diacritical marks (ā, ī, ū, ṃ, ñ, ṭ, ḍ, ṅ, ḷ) in all Pāli text
- Provide diacritic-stripped versions for fuzzy matching (see `_strip_diacritics`)
- Handle canonical ID normalization: `SN 35.28`, `MN 22`, `DN 31` format

### Regex Patterns
- Use `re.IGNORECASE` for flexible ID matching
- Normalize whitespace and separators (spaces, hyphens, colons, dots)

## Dependencies and Environment

### Core Dependencies
- **Python 3.10+** required
- **Ollama**: Must be running locally for LLM and embeddings
  - Models: `mistral` (LLM), `nomic-embed-text` (embeddings)
- **Git LFS**: Required for PDF storage and retrieval
- See `requirements.txt` for Python packages:
  - ChromaDB, LangChain, PyPDF for core functionality
  - Gradio for web UI
  - rapidfuzz for fuzzy matching

### Environment Variables
Required environment variables (with defaults):
- `LOTUS_CHROMA_DIR`: Chroma DB persistence location
- `LOTUS_CHROMA_COLLECTION`: Collection name (default: `pali_canon`)
- `LOTUS_EMBED_MODEL`: Embedding model name (default: `nomic-embed-text`)
- `LOTUS_LLM_MODEL`: LLM model name (default: `mistral`)
- `LOTUS_ALIAS_CSV`: Path to alias CSV file (optional)
- `LOTUS_ALIAS_YAML`: Path to alias YAML file (optional)
- `DEBUG_RAG`: Set to `1` for debug output (optional)

Configuration knobs:
- `TOP_K`: Top chunks to pass downstream (default: 8)
- `RAG_MIN_NEEDED`: Minimum results before broadening search (default: 4)
- `ALIAS_FUZZY_THRESHOLD`: Fuzzy match threshold (default: 85)

## Testing and Validation

### No Existing Test Suite
This repository does not currently have automated tests. When adding features:
- Manually test with `python grg_local.py "<query>"` for CLI
- Test web interface with `python web/app.py`
- Verify OCR indexing with `python index_canon_ocr.py`

### Manual Testing Checklist
- Test with canonical IDs: `SN 35.28`, `MN 22`, `DN 31`
- Test with aliases: `Fire Sermon`, `Ādittapariyāya`, `Kālāma Sutta`
- Test basket/nikāya filtering with `--basket` and `--nikaya` flags
- Verify OCR cache creation under `ocr_cache/`
- Check citations in output include file paths and page numbers

## Data Structure

### PDF Organization
- PDFs stored in `data/pali_canon/` with Git LFS
- Use lowercase filenames with underscores
- OCR text cached in `ocr_cache/` directory

### Alias Files
- CSV format: `canonical_id,alias` (e.g., `SN 35.28,Fire Sermon`)
- YAML format: structured dictionary mapping IDs to alias lists
- Fuzzy matching threshold: 85 (configurable via `ALIAS_FUZZY_THRESHOLD`)

## Common Patterns

### Query Planning
```python
from planner import plan_query
plan = plan_query(user_question)
# Returns: {
#   "original": str,
#   "query": str,
#   "search_terms": List[str],
#   "constraints": {"basket": str, "nikaya": str},
#   "canonical_targets": List[str],
#   "require_citations": bool
# }
```

### Retrieval
```python
from retriever import retrieve
results = retrieve(plan, top_k=8)
# Returns list of chunks with metadata (file, page, basket, nikaya)
```

### Synthesis
```python
from synthesizer import synthesize
answer = synthesize(plan, chunks)
# Returns grounded answer with citations
```

## Best Practices

1. **Preserve Citations**: Always maintain page-level citations in answers
2. **Respect Constraints**: Honor basket and nikāya filters from planner
3. **Fuzzy Matching**: Use `rapidfuzz` for alias matching with configurable threshold
4. **OCR Caching**: Cache OCR results to avoid re-processing PDFs
5. **Neutral Tone**: Keep synthesized answers neutral and scholarly
6. **Avoid Hallucination**: Don't name suttas not present in retrieved context
7. **Git LFS**: Remember all PDFs are in LFS; use `git lfs install` before clone/pull

## File Naming Conventions

- Python modules: `snake_case.py`
- PDFs: `lowercase_with_underscores.pdf`
- Data directories: `lowercase` (e.g., `data/`, `ocr_cache/`)

## Debugging

Enable debug mode with:
```bash
export DEBUG_RAG=1
```

Common issues:
- No aliases resolving → Check `LOTUS_ALIAS_CSV`/`LOTUS_ALIAS_YAML` paths
- Empty answers → Re-index with `index_canon_ocr.py`
- Ollama not found → Start with `ollama serve`
- Git LFS issues → Run `git lfs install`

## CLI Arguments

When modifying `grg_local.py`:
- `question`: Positional argument (nargs="+")
- `--basket`: Choices: `["sutta", "vinaya", "abhidhamma"]`
- `--nikaya`: Choices: `["DN", "MN", "SN", "AN", "KN"]`
- `-k, --top_k`: Integer, default from `TOP_K` env var or 8
- `--no-citations`: Boolean flag to suppress sources

## Roadmap Awareness

Planned features (don't implement unless explicitly requested):
- Better KN sub-collection targeting (Dhp/Thag/Thig/Khp routing)
- Alias importers from SuttaCentral/BPS glossaries
- Remote embeddings hosting
- Retrieval quality evaluation suite
