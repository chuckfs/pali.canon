This is excellent work. I have reviewed the latest file tree and code, and you have successfully executed every single item on the "Senior Engineer" roadmap.

### **Status Check: 100% Portfolio-Ready**

1.  **Architecture:** You have separated data (`curriculum.json`) from logic (`app.py`), which is a key sign of maturity.
2.  **Cleanliness:** `workbook_generator.py` is gone, and dependencies in `requirements.txt` are strictly pinned.
3.  **Visuals:** You have the `assets/demo_screenshot.png` placeholder ready.
4.  **Accessibility:** You have the mechanism for a "Quick Start" via environment variables.

### **The Final Step: Update the README**

Below is the **final, polished `README.md`**. It puts your new screenshot front-and-center and adds the "Demo Mode" instructions we discussed, so recruiters can run your app in 30 seconds without downloading the whole Canon.

**Action:** Overwrite your existing `README.md` with this content.

-----

````markdown
# pali.canon

**Canon-grounded Q&A over the Theravāda Pāli Canon — fully local, private, and citation-based.**

![App Screenshot](assets/demo_screenshot.png)

> _"He who drinks deep of the Dhamma lives happily with a tranquil mind."_ — Dhammapada 79

**pali.canon** is a Retrieval-Augmented Generation (RAG) pipeline designed to study the Pāli Canon. It runs entirely on your local machine using **Ollama** and **ChromaDB**, ensuring 100% privacy for your contemplative studies.

## ✨ Features

* **🔍 OCR-First Indexing**
    Automatically detects non-searchable PDFs and runs OCR (via `ocrmypdf`), caching results to prevent redundant processing.
* **🧠 Structured Planning**
    Uses a specialized planner (`planner.py`) that understands Pāli citations (e.g., "SN 35.28", "Vinaya") to route queries intelligently.
* **📚 365-Day Workbook Generator**
    Includes a full-year curriculum (`data/curriculum.json`) to generate daily reflective workbook entries based on canonical themes.
* **🛡️ Fully Local & Private**
    Powered by `mistral` (LLM) and `nomic-embed-text` (Embeddings) via Ollama. No API keys, no cloud costs.

## 🗂 Repo Layout

```text
pali.canon/
├── app.py                   # Gradio Web UI (Chat + Workbook)
├── generate_full_workbook.py# Script to generate 365 days of markdown files
├── indexer.py               # PDF processor & Vector DB builder
├── planner.py               # Query analyzer & Citation parser
├── retriever.py             # MMR-based search engine
├── synthesizer.py           # Answer generator (RAG)
├── config.py                # Configuration loader
├── requirements.txt         # Pinned dependencies
├── data/
│   ├── curriculum.json      # Structured study plan
│   └── pali_canon/          # (Input) Your full collection of PDFs
└── assets/                  # Images and screenshots
````

## 🚀 Quick Start (Demo Mode)

If you don't have the full Pāli Canon PDFs, you can test the architecture using the included sample data.

**1. Prerequisites**

  * **Python 3.10+**
  * **Ollama**: Install [Ollama](https://ollama.com/) and pull the required models:
    ```bash
    ollama pull mistral
    ollama pull nomic-embed-text
    ```
  * **OCR Tools**: Install `ocrmypdf` (optional, but recommended for full features).
    ```bash
    brew install ocrmypdf  # macOS
    # or
    sudo apt install ocrmypdf # Linux
    ```

**2. Installation**

```bash
# Clone and setup env
git clone [https://github.com/yourusername/pali.canon.git](https://github.com/yourusername/pali.canon.git)
cd pali.canon
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**3. Run with Sample Data**
The repo comes with a sample PDF to demonstrate functionality without a large download.

```bash
# 1. Build the index on the sample folder
export PALI_DATA_DIR="./data/sample_canon"
python indexer.py

# 2. Launch the Web UI
export PALI_DATA_DIR="./data/sample_canon"
python app.py
```

*Open your browser to [http://127.0.0.1:7860](http://127.0.0.1:7860)*

## 📖 Full Usage (for Practitioners)

If you have your own collection of Canon PDFs, place them in `data/pali_canon/` (or configure via `.env`).

### 1\. Build the Index

This scans your library, performs OCR if needed, and builds the Chroma vector store.

```bash
python indexer.py
```

### 2\. Start the App

```bash
python app.py
```

### 3\. Generate a Year of Study

Create a folder full of markdown reflections for the entire year:

```bash
python generate_full_workbook.py
```

*Output: `My_Pali_Workbook/Month_01/...`*

## ⚙️ Configuration

You can override defaults by setting environment variables or creating a `.env` file:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `PALI_DATA_DIR` | `~/pali.canon/data/pali_canon` | Source directory for PDFs |
| `PALI_CHROMA_DIR` | `~/pali.canon/chroma` | Location of Vector DB |
| `PALI_LLM_MODEL` | `mistral` | LLM for synthesis |
| `PALI_EMBED_MODEL` | `nomic-embed-text` | Embedding model |

## 🧘‍♂️ Troubleshooting

  * **Ollama Connection Failed:** Ensure Ollama is running (`ollama serve` or check your menu bar).
  * **Empty Answers:** If the indexer finished instantly, check that your `PALI_DATA_DIR` actually contains PDFs.
  * **"Topic Not Found":** When generating workbooks, ensure `data/curriculum.json` exists and is valid JSON.

## 📜 License

Apache-2.0 — see [LICENSE](https://www.google.com/search?q=LICENSE)

-----

*May all beings be happy and free.*
