#!/usr/bin/env bash
set -euo pipefail

# Ensure Chroma dir exists (use a Railway Volume mounted at /var/chroma)
mkdir -p "${LOTUS_CHROMA_DIR:-/var/chroma}"

echo "PALI_PROJECT_ROOT=${PALI_PROJECT_ROOT:-/app}"
echo "LOTUS_CHROMA_DIR=${LOTUS_CHROMA_DIR:-/var/chroma}"
echo "OLLAMA_URL=${OLLAMA_URL:-<unset>} (must point to a running Ollama server)"

# Optional: simple reachability check for remote Ollama
if [ -n "${OLLAMA_URL:-}" ]; then
  echo "Checking OLLAMA_URL..."
  curl -sSf "${OLLAMA_URL}/api/tags" >/dev/null || \
    echo "WARN: Could not reach OLLAMA_URL (${OLLAMA_URL}). The app may start but model calls will fail."
fi

# Start your app (Gradio, FastAPI, etc.)
python web/app.py
