# Dockerfile (slim, no Ollama inside)
FROM python:3.11-slim

# minimal OS deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates tini \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# install deps first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# add app
COPY . .

# make scripts executable
RUN chmod +x start.sh

# sensible defaults (override in Railway Variables)
ENV PALI_PROJECT_ROOT=/app \
    LOTUS_CHROMA_COLLECTION=lotus_canon \
    LOTUS_EMBED_MODEL=nomic-embed-text \
    LOTUS_LLM_MODEL=mistral \
    LOTUS_CHROMA_DIR=/var/chroma \
    OLLAMA_URL=https://YOUR-REMOTE-OLLAMA:11434

# use tini as entrypoint for clean signals
ENTRYPOINT ["/usr/bin/tini", "--"]

EXPOSE 7860
CMD ["./start.sh"]
