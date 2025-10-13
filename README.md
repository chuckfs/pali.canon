# 🪷 CLI: pali "your query"

Run your local Pāli Canon RAG assistant directly from the terminal.

⸻

## 1️⃣ Install & Set Up

### Clone with Git LFS

git lfs install
git clone git@github.com:chuckfs/PaLi-CANON.git
cd PaLi-CANON

### Python Environment

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

### (Optional) Build / Rebuild the Index

python3 index_canon.py ./data


⸻

## 2️⃣ Add the CLI to Your PATH

### macOS / zsh

echo 'export PATH="$HOME/PaLi-CANON/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

### Now you can run the assistant from anywhere using pali.

⸻

## 3️⃣ Environment Defaults (override anytime)

### These are automatically used unless you set your own:

export LOTUS_CHROMA_DIR="$HOME/PaLi-CANON/chroma"
export LOTUS_CHROMA_COLLECTION="lotus_canon"
export LOTUS_EMBED_MODEL="nomic-embed-text"

### 💡 Tip: Add those lines to your ~/.zshrc so they persist between sessions.

⸻

## 4️⃣ Run It

### pali "Give a 1-page beginner lesson on Satipaṭṭhāna with a *Key passage* (≤120 words) and FULL Canon citations."

You’ll see:
	•	the Lotus banner
	•	a Sources section (from your local PDFs)
	•	the AI-generated lesson

### To silence the banner for scripts:

LOTUS_NO_BANNER=1 pali "..."


⸻

## 🌿 Alternative (no PATH change)

### If you’d rather not edit your PATH, add this function to ~/.zshrc:

pali() {
  local PROJECT="$HOME/PaLi-CANON"
  [ -f "$PROJECT/.venv/bin/activate" ] && source "$PROJECT/.venv/bin/activate"
  export LOTUS_CHROMA_DIR="${LOTUS_CHROMA_DIR:-$PROJECT/chroma}"
  export LOTUS_CHROMA_COLLECTION="${LOTUS_CHROMA_COLLECTION:-lotus_canon}"
  export LOTUS_EMBED_MODEL="${LOTUS_EMBED_MODEL:-nomic-embed-text}"
  echo ""
  echo "⸻ 𑁍 ⸻"
  echo "  pali is thinking..."
  echo "⸻ 𑁍 ⸻"
  echo ""
  python3 "$PROJECT/query_canon.py" "$@"
}

### Then run:

source ~/.zshrc
pali "tell me about the Dhammapada"


⸻

## ⚙️ Troubleshooting

“command not found: pali”
→ Ensure bin/ is on your PATH (see step 2) or that the function is in ~/.zshrc and you’ve run source ~/.zshrc.

No sources / empty results
→ Check your environment:

echo $LOTUS_CHROMA_DIR $LOTUS_CHROMA_COLLECTION $LOTUS_EMBED_MODEL

and verify that your index exists in $LOTUS_CHROMA_DIR.

Virtual env not active
→ The wrapper auto-activates .venv if it exists in the project root.

⸻

Would you like me to generate a README banner + badges section (e.g., ![Built with Mistral](...) + tagline + installation badges) so the top of your GitHub page looks professional and unified with the Lotus style?
