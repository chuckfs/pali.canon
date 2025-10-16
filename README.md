# pali.canon (chuckfs)

Canon-grounded Q&A over the Theravāda Pāli Canon with page-level citations.
Pipeline: G-RAG-G — planner → retriever → synthesizer — using Mistral via Ollama and Chroma for embeddings.

⚠️ All PDFs are stored with Git LFS. Make sure LFS is installed before cloning/pulling.


## Features
- OCR-first indexing (index_canon_ocr.py) so every page is searchable (cached under ocr_cache/).
- Data-driven aliases (CSV/YAML) + fuzzy matching → queries like “Fire Sermon” resolve to SN 35.28 (Ādittapariyāya).
- Structured planner infers basket (Sutta/Vinaya/Abhidhamma) & Nikāya (DN/MN/SN/AN/KN).
- Two-phase retrieval: filtered search → broaden if results are thin, plus hybrid ranking (vector + BM25).
- Grounded synthesis: neutral, concise answers that cite files + pages; guardrails to avoid naming suttas not in context.
- CLI and Gradio app UI.


## Repo layout

PaLi-CANON/
├─ data/
│  └─ pali_canon/                 # your organized Canon PDFs (lowercase, underscores)
├─ ocr_cache/                     # text cache produced by OCR indexer
├─ web/                           # optional web app bits (gradio wrapper lives here too)
├─ alias_loader.py                # loads aliases from CSV/YAML + fuzzy matching
├─ index_canon.py                 # baseline indexer (extract text if present)
├─ index_canon_ocr.py             # OCR-first indexer (always OCR); caches output
├─ planner.py                     # query → plan (IDs, aliases, basket/nikāya)
├─ retriever.py                   # Chroma + hybrid ranking (vector + BM25)
├─ synthesizer.py                 # Mistral via Ollama; grounded answers + citations
├─ grg_local.py                   # CLI entrypoint
├─ requirements.txt
└─ LICENSE                        # Apache-2.0



## Quickstart

### 0) Prereqs
#### Python 3.10+
#### Ollama running locally (for Mistral) → https://ollama.com

ollama pull mistral
ollama pull nomic-embed-text


#### Git LFS (for the PDFs)

git lfs install



### 1) Create & activate a venv

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

### 2) Environment variables (sane defaults)

#### where to persist the Chroma DB
export LOTUS_CHROMA_DIR="$HOME/PaLi-CANON/chroma"
#### collection name
export LOTUS_CHROMA_COLLECTION="pali_canon"
#### embeddings + LLM (Ollama model names)
export LOTUS_EMBED_MODEL="nomic-embed-text"
export LOTUS_LLM_MODEL="mistral"

#### optional: point to your aliases file(s)
export LOTUS_ALIAS_CSV="$HOME/PaLi-CANON/data/aliases/aliases.csv"
#### export LOTUS_ALIAS_YAML="$HOME/PaLi-CANON/data/aliases/aliases.yaml"

#### optional: debug
export DEBUG_RAG=1

### 3) Index the corpus

OCR-first (recommended—guarantees text for every page):

python index_canon_ocr.py
#### -> builds chroma under $LOTUS_CHROMA_DIR and caches OCR under ocr_cache/

#### (If your PDFs already have perfect text layers, you can use index_canon.py instead.)


## Using It

### CLI

#### Ask a question (auto planner)
python grg_local.py "Where is the Fire Sermon (Ādittapariyāya) and what does it teach?"

#### Nudge retrieval if you know the basket/Nikāya
python grg_local.py "Karaniya Metta guidance" --nikaya KN --basket sutta

#### Control retrieval size
python grg_local.py "benefits of metta" -k 12

### Gradio app

python web/app.py
##### → open http://127.0.0.1:7860



## Aliases (titles, nicknames, Pāli variants)

#### Aliases are not hard-coded; they’re loaded from CSV/YAML and matched fuzzily.
### 1.	Create a CSV (one alias per row):

canonical_id,alias
SN 35.28,Fire Sermon
SN 35.28,Ādittapariyāya
AN 3.65,Kālāma Sutta
Sn 1.8,Karaṇīya Mettā
DN 31,Sigālovāda

### 2.	Point the loader:

export LOTUS_ALIAS_CSV="$HOME/PaLi-CANON/data/aliases/aliases.csv"

#### Tip: Generate a manifest of all PDFs (with guessed IDs) to help seed aliases:

python make_manifest.py
#### writes data/manifest.csv with relpath, basket, nikaya, pages, maybe_id




## How it works (short)
1.	Planner (planner.py)
	•	Extracts explicit IDs: SN 35.28, MN22, DN-31, etc.
	•	Resolves nicknames via alias table (CSV/YAML) + fuzzy.
	•	Infers constraints: basket + nikaya.
	2.	Retriever (retriever.py)
	•	Phase A: vector search filtered by constraints (canon + basket + nikāya).
	•	If too few hits, Phase B: broaden to canon-only.
	•	Hybrid rank: vector + BM25.
	•	Gentle rerank toward target/alias tokens; outputs page-level citations.
	3.	Synthesizer (synthesizer.py)
	•	Mistral (Ollama) composes a neutral answer grounded in the snippets.
	•	Won’t name/number suttas unless seen in the context; appends Sources + a confidence score.


## Configuration knobs
- TOP_K — top chunks to pass downstream (default 8)
- RAG_MIN_NEEDED — if Phase A returns fewer than this, broaden (default 4)
- ALIAS_FUZZY_THRESHOLD — fuzzy match threshold (default 85)
- RAG_BASKET — force basket (sutta|vinaya|abhidhamma) regardless of planner

### Set via env, e.g.:

export TOP_K=10
export RAG_MIN_NEEDED=3
export ALIAS_FUZZY_THRESHOLD=88



## Troubleshooting
- No aliases resolving? Ensure LOTUS_ALIAS_CSV/YAML points to a real file.
- Empty answers? Re-index with index_canon_ocr.py, then confirm LOTUS_CHROMA_COLLECTION=pali_canon.
- Wrong Nikāya? Use CLI flags --nikaya / --basket to verify retrieval path.
- Ollama not found? Start it: ollama serve (in another terminal).
- Large pulls fail? Ensure Git LFS is installed: git lfs install.


## Roadmap
- Better KN sub-collection targeting (Dhp/Thag/Thig/Khp routing).
- Alias importers from SuttaCentral/BPS glossaries.
- Optional server mode with embeddings hosted remotely.
- Eval suite for retrieval quality.


## License

This project is licensed under the Apache-2.0 license — see LICENSE.


## Acknowledgments
- Community translators and editors of the Pāli Canon.
- Open-source projects powering this stack: Ollama, Chroma, LangChain, rank_bm25, rapidfuzz.
