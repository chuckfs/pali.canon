FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates tini \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x start.sh

ENV PALI_PROJECT_ROOT=/app \
    LOTUS_CHROMA_COLLECTION=lotus_canon \
    LOTUS_EMBED_MODEL=nomic-embed-text \
    LOTUS_LLM_MODEL=mistral \
    LOTUS_CHROMA_DIR=/var/chroma \
    OLLAMA_URL=pali-https://canon-production.up.railway.app

ENTRYPOINT ["/usr/bin/tini", "--"]
EXPOSE 7860
CMD ["./start.sh"]
