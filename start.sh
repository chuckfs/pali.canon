#!/usr/bin/env bash
set -euo pipefail

# start ollama in background
ollama serve &
# wait for it to come up
for i in {1..60}; do
  if curl -s http://127.0.0.1:11434/api/tags >/dev/null; then break; fi
  echo "waiting for ollama..."; sleep 1
done

# pull models you use
ollama pull nomic-embed-text
ollama pull mistral

# ensure Chroma dir exists (Railway volume mount recommended)
export LOTUS_CHROMA_DIR="${LOTUS_CHROMA_DIR:-/var/chroma}"
mkdir -p "$LOTUS_CHROMA_DIR"

# launch your app (Gradio)
python web/app.py
