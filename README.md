# CLI: pali "your query"

## 1) Install & set up

### Clone with Git LFS
git lfs install
git clone git@github.com:chuckfs/lotus-canon.git
cd lotus-canon

### Python env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

### (Optional) Build / rebuild the index
python3 index_canon.py ./data

## 2) Add the CLI to your PATH (so pali works everywhere)

### macOS / zsh
echo 'export PATH="$HOME/lotus-canon/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

## 3) Environment defaults (override anytime)

### These are the defaults the CLI will use if not set:
export LOTUS_CHROMA_DIR="$HOME/lotus-canon/chroma"
export LOTUS_CHROMA_COLLECTION="lotus_canon"
export LOTUS_EMBED_MODEL="nomic-embed-text"

Tip: Add those to ~/.zshrc so they persist.

## 4) Run it

pali "Give a 1-page beginner lesson on Satipaṭṭhāna with a *Key passage* (≤120 words) and FULL Canon citations."

You should see a banner, a Sources section (from your local PDFs), then the answer.
To silence the banner for scripts: LOTUS_NO_BANNER=1 pali "...".

⸻

## Alternative (no PATH change): shell function

pali() {
  local PROJECT="$HOME/lotus-canon"
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

## Then:

source ~/.zshrc
pali "tell me about the Dhammapada"


⸻

## Troubleshooting
	•	“command not found: pali”
Ensure either bin/ is on PATH (see step 2) or the shell function is in ~/.zshrc and you ran source ~/.zshrc.
	•	No sources / empty results
Check env vars:
echo $LOTUS_CHROMA_DIR $LOTUS_CHROMA_COLLECTION $LOTUS_EMBED_MODEL
and that your index exists in $LOTUS_CHROMA_DIR.
	•	Virtual env not active
The wrapper auto-activates .venv if it exists in the repo root.
