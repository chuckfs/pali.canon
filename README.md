# 🪷 PaLi-CANON  
*A Local + Cloud Pāli Canon Research & Lesson Generator*

[![Hugging Face Space](https://img.shields.io/badge/Demo-Lotus%20Canon%20Space-blue?logo=huggingface)](https://huggingface.co/spaces/chkxd/lotus-canon)
[![GitHub Repo](https://img.shields.io/badge/GitHub-chuckfs%2FPaLi--CANON-black?logo=github)](https://github.com/chuckfs/PaLi-CANON)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

**PaLi-CANON** is a *Generative Retrieval-Augmented AI* (g-RAG-g) system trained on the entire Pāli Canon — capable of teaching, referencing, and generating lessons with accurate citations.

It runs locally via the `pali` CLI **or** in-browser via the [Lotus Canon Hugging Face Space](https://huggingface.co/spaces/chkxd/lotus-canon).

---

## 🌐 Try It Instantly (Cloud)
**No setup required →**
👉 [**Open the Lotus Canon Space**](https://huggingface.co/spaces/chkxd/lotus-canon)

Type a question like:

What are the Four Noble Truths in the Majjhima Nikāya?

The app will reason through the indexed Canon texts and return passages with full citations.

---

## 💻 Run Locally (CLI)

### 1️⃣ Install & Set Up
git lfs install
git clone git@github.com:chuckfs/PaLi-CANON.git
cd PaLi-CANON

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 index_canon.py ./data   # optional: build index

### 2️⃣ Add the CLI

echo 'export PATH="$HOME/PaLi-CANON/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

### 3️⃣ Environment Defaults

export LOTUS_CHROMA_DIR="$HOME/PaLi-CANON/chroma"
export LOTUS_CHROMA_COLLECTION="lotus_canon"
export LOTUS_EMBED_MODEL="nomic-embed-text"

### 4️⃣ Run It

pali "Give a 1-page beginner lesson on Satipaṭṭhāna with a *Key passage* (≤120 words) and full Canon citations."


⸻

## 🧠 Features
	•	🪷 Full Canon context — Dīgha, Majjhima, Saṃyutta, Aṅguttara, and Khuddaka Nikāyas
	•	🧩 Local RAG engine — Chroma DB + Mistral + Ollama embeddings
	•	🗂️ Index builder — OCR fallback for scanned PDFs
	•	🖥️ Cross-platform CLI (pali) or web interface
	•	🪞 Ethical sourcing — grounded in open Pāli translations

⸻

## 🧰 Tech Stack

Layer	Tool
Embeddings	nomic-embed-text (Ollama)
Vector DB	Chroma
LLM	Mistral
Frontend (Space)	Gradio
Backend	Python 3
Host	Hugging Face Spaces + GitHub


⸻

## ⚙️ Troubleshooting
	•	command not found: pali → ensure $PATH includes PaLi-CANON/bin
	•	No sources / empty results → check $LOTUS_CHROMA_DIR exists
	•	Virtual env inactive → wrapper auto-activates .venv in repo root

⸻

## 📜 License

MIT — see LICENSE.

⸻

## 🌸 Credits

Lotus Canon • by @chuckfs
Pāli Canon RAG system — built with Mistral, Chroma, and reverence.
