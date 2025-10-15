FROM python:3.11-slim

# basics
RUN apt-get update && apt-get install -y curl gnupg && rm -rf /var/lib/apt/lists/*

# install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# app
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# perms
RUN chmod +x start.sh

# default envs (tweak if you like)
ENV PALI_PROJECT_ROOT=/app \
    LOTUS_CHROMA_COLLECTION=lotus_canon \
    LOTUS_EMBED_MODEL=nomic-embed-text \
    LOTUS_LLM_MODEL=mistral \
    OLLAMA_URL=http://127.0.0.1:11434

EXPOSE 7860
CMD ["./start.sh"]
