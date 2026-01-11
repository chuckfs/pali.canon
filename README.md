# pali.canon

**Local, private, citation-grounded Q&A for the Pāli Canon.**

> *"Careful attention is the path to the Deathless."* — Dhammapada 21

pali.canon is a Retrieval-Augmented Generation (RAG) system for studying the Theravāda Buddhist scriptures. It runs entirely on your local machine using Ollama, ensuring complete privacy for your contemplative practice.

## What It Does

1. **Indexes your PDF library** — Processes the Pāli Canon (or any PDF collection), runs OCR when needed, and builds a searchable vector database.
2. **Answers questions with citations** — Uses semantic search to find relevant passages, then generates answers grounded in the retrieved texts.
3. **Generates study materials** — Creates daily workbook entries following a structured 365-day curriculum.

## How It Works

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Your      │     │   Indexer   │     │  ChromaDB   │     │   Ollama    │
│   PDFs      │────▶│  + OCR      │────▶│  (vectors)  │     │  (LLM)      │
└─────────────┘     └─────────────┘     └──────┬──────┘     └──────┬──────┘
                                               │                   │
                    ┌──────────────────────────┘                   │
                    │                                              │
                    ▼                                              │
              ┌─────────────┐     ┌─────────────┐     ┌────────────┘
              │  Retriever  │────▶│ Synthesizer │────▶│  Answer
              │  (search)   │     │  (generate) │     │  + Sources
              └─────────────┘     └─────────────┘     └────────────
```

1. **Indexing**: PDFs are OCR'd (if needed), split into overlapping chunks, embedded with `nomic-embed-text`, and stored in ChromaDB.
2. **Query Planning**: Your question is analyzed for canonical citations (e.g., "SN 35.28"), basket hints (Vinaya/Sutta/Abhidhamma), and keywords.
3. **Retrieval**: Maximal Marginal Relevance search finds diverse, relevant passages.
4. **Synthesis**: Mistral generates an answer grounded in the retrieved passages, with source citations.

## Prerequisites

- **Python 3.10+**
- **Ollama** — Install from [ollama.com](https://ollama.com)
- **OCRmyPDF** (optional but recommended)
  ```bash
  # macOS
  brew install ocrmypdf
  
  # Ubuntu/Debian
  sudo apt install ocrmypdf
  ```

## Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/pali.canon.git
cd pali.canon

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Pull required Ollama models
ollama pull mistral
ollama pull nomic-embed-text
```

## Quick Start (Demo Mode)

Test the system with included sample data:

```bash
# Build index on sample data
export PALI_DATA_DIR="./data/sample_canon"
python indexer.py

# Launch the web interface
python app.py
# Open http://127.0.0.1:7860
```

## Full Usage

### 1. Add Your PDFs

Place your Pāli Canon PDFs in `data/pali_canon/` organized by basket:
```
data/pali_canon/
├── vinaya_pitaka/
├── sutta_pitaka/
│   ├── digha_nikaya/
│   ├── majjhima_nikaya/
│   └── ...
└── abhidhamma_pitaka/
```

### 2. Build the Index

```bash
python indexer.py
```

This scans all PDFs, runs OCR on image-based files (cached for future runs), and builds the vector database. First run may take 1-2 hours for a full Canon collection.

### 3. Start the Application

```bash
python app.py
```

### 4. Generate Study Workbook (Optional)

Create a year's worth of daily study entries:

```bash
python generate_full_workbook.py
# Output: My_Pali_Workbook/
```

## Configuration

Set via environment variables or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `PALI_DATA_DIR` | `~/pali.canon/data/pali_canon` | Source PDF directory |
| `PALI_CHROMA_DIR` | `~/pali.canon/chroma` | Vector database location |
| `PALI_LLM_MODEL` | `mistral` | Ollama model for generation |
| `PALI_EMBED_MODEL` | `nomic-embed-text` | Ollama model for embeddings |

## Project Structure

```
pali.canon/
├── app.py              # Gradio web interface
├── indexer.py          # PDF → vectors pipeline
├── planner.py          # Query analysis
├── retriever.py        # Vector search
├── synthesizer.py      # Answer generation
├── config.py           # Configuration
├── data/
│   ├── curriculum.json # 365-day study plan
│   └── pali_canon/     # Your PDFs (gitignored)
└── docs/               # Documentation
```

## Design Goals

- **Privacy first** — Everything runs locally; no data leaves your machine
- **Citation grounded** — Answers include source references
- **Scholarly tone** — Responses encourage reflection, not just information delivery
- **Accessible** — Works on consumer hardware (M1 Mac, modest GPU)

## Non-Goals (Current Limitations)

- **Not a translation tool** — Works with existing translations, doesn't translate Pāli
- **Not verse-level precise** — Retrieves by page/chunk, not by sutta number (yet)
- **Not multi-user** — Designed for personal study, not concurrent access
- **No quality guarantees** — Answers may contain errors; always verify against sources

## Roadmap

- [ ] Structured citation metadata (sutta numbers, PTS references)
- [ ] Evaluation framework with golden dataset
- [ ] Hybrid search (semantic + keyword)
- [ ] Cross-encoder reranking
- [ ] Pāli term expansion (craving ↔ taṇhā)

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Connection refused" | Ensure Ollama is running: `ollama serve` |
| Empty answers | Check `PALI_DATA_DIR` points to actual PDFs |
| Slow first run | OCR is processing; results are cached for future runs |
| "Topic not found" | Verify `data/curriculum.json` exists and is valid JSON |

## License

Apache-2.0

---

*Sabbadānaṃ dhammadānaṃ jināti.* — The gift of Dhamma excels all gifts.
