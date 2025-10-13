# Lotus Canon
Pāli Canon RAG project — built by chuckfs

## Quick start
### 1) Clone with LFS
git lfs install
git clone git@github.com:chuckfs/lotus-canon.git
cd lotus-canon

### 2) Python env
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

### 3) Env (shell profile or export per session)
export LOTUS_CHROMA_DIR="$HOME/lotus-canon/chroma" \
export LOTUS_CHROMA_COLLECTION="lotus_canon" \
export LOTUS_EMBED_MODEL="nomic-embed-text" \

### 4) (Optional) Build / rebuild index
python3 index_canon.py ./data

### 5) Ask Pāli
pali "Give a 1-page beginner lesson on Satipaṭṭhāna. Include a *Key passage* (≤120 words) with FULL Canon citation."
