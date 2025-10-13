# models_local.py — talk to local Ollama (Mistral)
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral"  # or "mistral:7b-instruct" if you pulled a tag

def llm(prompt: str, system: str = "", temperature: float = 0.1, timeout: int = 120) -> str:
    full = (system + "\n" if system else "") + prompt
    r = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "prompt": full,
        "stream": False,
        "temperature": temperature
    }, timeout=timeout)
    r.raise_for_status()
    return r.json().get("response", "").strip()
