# pali.canon

Canon-grounded Q&A over the Theravāda Pāli Canon — fully local, private, and citation-based.
Pipeline: LLM → RAG → LLM (planner → retriever → synthesizer), powered by Ollama + Chroma.

⚡ No API keys, no cloud calls — runs entirely on your computer.


## ✨ Features
- OCR-first indexing (indexer.py)
Every page of every Canon PDF becomes searchable (stored in ocr_cache/).
- Structured planning (planner.py)
Parses IDs like SN 35.28 and infers context (Sutta / Vinaya / Abhidhamma).
- Accurate retrieval (retriever.py)
Uses nomic-embed-text embeddings + MMR search for diverse, relevant results.
- Grounded synthesis (synthesizer.py)
Local Mistral model via Ollama generates neutral, citation-rich answers.
	- Dual interface:
🧠 Command-line (pali) — fast and scriptable.
💬 Gradio web app (app.py) — chat-style experience.


## 🗂 Repo layout

pali.canon/
├─ data/
│  └─ pali_canon/          # your Canon PDFs
├─ ocr_cache/              # OCR’d copies (auto-created)
├─ .env                    # environment variables
├─ app.py                  # Gradio app (LLM→RAG→LLM)
├─ cli.py                  # command-line interface
├─ config.py               # loads env vars
├─ indexer.py              # OCR + page-level indexer
├─ planner.py              # query planner
├─ retriever.py            # search engine
├─ synthesizer.py          # grounded answer generator
└─ requirements.txt



## 🚀 Quickstart

### 0) Prereqs

🐍 Python 3.10+

🦙 Ollama (local LLM host)

brew install --cask ollama
brew services start ollama
ollama pull mistral
ollama pull nomic-embed-text

🧾 OCR tools

brew install ocrmypdf mupdf

📦 Git LFS (for PDFs)

git lfs install



### 1) Create your virtual environment

cd ~/pali.canon
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt



### 2) Environment setup

In ~/.zshrc (already done if you cloned from this repo):

# 🪷 Pali Canon environment variables
export PALI_PROJECT_ROOT="$HOME/pali.canon"
export PALI_CHROMA_DIR="$PALI_PROJECT_ROOT/chroma"
export PALI_CHROMA_COLLECTION="pali_canon"
export PALI_EMBED_MODEL="nomic-embed-text"

Then add the magic shortcut:

hello() {
  if [[ "$1" == "pali" ]]; then
    echo ""
    echo "🪷 Welcome back to pali.canon, Charlie (or future scholar)."
    echo "Activating virtual environment..."
    cd ~/pali.canon || return
    source .venv/bin/activate
    echo ""
    echo "📘 Ready. Try:"
    echo "   pali \"What is the Fire Sermon?\""
    echo ""
  else
    echo "Usage: hello pali"
  fi
}

Reload your shell:

source ~/.zshrc



### 3) Build the index (one-time OCR)

hello pali
python indexer.py

This creates the searchable Chroma database and caches OCR’d pages under ocr_cache/.


### 4) Ask questions — two ways

🧠 CLI

pali "What is the Fire Sermon?"

💬 Gradio UI

python app.py

Open the printed local URL (e.g., http://127.0.0.1:7860).


## 💡 Examples

pali "What does the Buddha say about craving?"
pali "Explain the simile of the saw."
pali "Where is the Kālāma Sutta found?"

Each response cites the exact PDF + page (e.g., samyutta_nikaya1.pdf — p.112).


## ⚙️ Config knobs

Variable	Default	Description
PALI_LLM_MODEL	mistral	Ollama LLM for synthesis
PALI_EMBED_MODEL	nomic-embed-text	embedding model
PALI_CHROMA_COLLECTION	pali_canon	Chroma collection name
TOP_K	8	chunks to pass downstream
RAG_MIN_NEEDED	4	widen search if fewer hits



## 🧘‍♂️ Troubleshooting
- Ollama connection failed → brew services start ollama
- Empty answers? → re-run python indexer.py
- No .venv? → recreate it:
python3 -m venv .venv && source .venv/bin/activate
- Show hidden files: ⌘ + Shift + .


## 🛠 Advanced
- Auto-activate: hello pali moves to ~/pali.canon and activates .venv.
- Rebuild index anytime: python indexer.py
- Update everything + push:

git add -A
git commit -m "update pipeline"
git push origin main




## 📜 License

Apache-2.0 — see LICENSE


## 🙏 Acknowledgments
- Community translators and editors of the Pāli Canon
- Open-source projects powering this stack: Ollama, Chroma, LangChain, PyMuPDF, rapidfuzz


hello pali
pali "What is the Fire Sermon?"
