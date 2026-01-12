# config.py
"""
Central configuration for pali.canon.

Goals:
- Single source of truth for paths + tuning knobs
- Safe defaults
- Optional validation that won't break pytest runs

Usage:
- Normal runs (no validation):
    python app.py
    python indexer.py

- Validate config (recommended when debugging setup):
    PALI_VALIDATE_CONFIG=1 python indexer.py

- Also validate Ollama connectivity:
    PALI_VALIDATE_CONFIG=1 PALI_VALIDATE_OLLAMA=1 python app.py
"""

import os
import sys
import subprocess
from dotenv import load_dotenv

load_dotenv()

# =========================
# Retrieval settings
# =========================
TOP_K = int(os.getenv("TOP_K", "8"))
RAG_MIN_NEEDED = int(os.getenv("RAG_MIN_NEEDED", "4"))  # Widen search if fewer than this

# =========================
# Synthesis settings
# =========================
MIN_HITS = int(os.getenv("RAG_MIN_HITS", "2"))  # Refuse confident answer if fewer than this

# =========================
# Chunking settings
# =========================
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))

# =========================
# Paths / models
# =========================
ROOT = os.path.expanduser(os.getenv("PALI_PROJECT_ROOT", "~/pali.canon"))
DATA = os.path.expanduser(os.getenv("PALI_DATA_DIR", f"{ROOT}/data/pali_canon"))
CHROMA = os.path.expanduser(os.getenv("PALI_CHROMA_DIR", f"{ROOT}/chroma"))

COLL = os.getenv("PALI_CHROMA_COLLECTION", "pali_canon")
LLM = os.getenv("PALI_LLM_MODEL", "mistral")
EMBED = os.getenv("PALI_EMBED_MODEL", "nomic-embed-text")

ALIAS = os.path.expanduser(os.getenv("PALI_ALIAS_CSV", f"{ROOT}/config/aliases.csv"))

# Ensure vector store directory exists (safe side effect)
os.makedirs(CHROMA, exist_ok=True)


def validate_config() -> None:
    """
    Validate runtime configuration.

    IMPORTANT:
    - This is opt-in to avoid breaking pytest runs.
    - Enable with: PALI_VALIDATE_CONFIG=1
    - Enable Ollama check with: PALI_VALIDATE_OLLAMA=1
    """
    errors = []

    # --- Paths ---
    if not os.path.exists(DATA):
        errors.append(f"PALI_DATA_DIR not found: {DATA}")

    # ALIAS is optional (planner can still function without it),
    # but warn loudly if missing.
    if not os.path.exists(ALIAS):
        # Not fatal — just warning.
        print(f"⚠️  Warning: Alias CSV not found (alias expansion disabled): {ALIAS}")

    # --- Numeric sanity ---
    if TOP_K <= 0 or TOP_K > 100:
        errors.append(f"TOP_K out of range (1..100): {TOP_K}")

    if RAG_MIN_NEEDED < 0 or RAG_MIN_NEEDED > 100:
        errors.append(f"RAG_MIN_NEEDED out of range (0..100): {RAG_MIN_NEEDED}")

    if MIN_HITS < 0 or MIN_HITS > 100:
        errors.append(f"RAG_MIN_HITS (MIN_HITS) out of range (0..100): {MIN_HITS}")

    if CHUNK_SIZE < 100 or CHUNK_SIZE > 10000:
        errors.append(f"CHUNK_SIZE out of range (100..10000): {CHUNK_SIZE}")

    if CHUNK_OVERLAP < 0:
        errors.append(f"CHUNK_OVERLAP must be >= 0: {CHUNK_OVERLAP}")

    if CHUNK_OVERLAP >= CHUNK_SIZE:
        errors.append(
            f"CHUNK_OVERLAP must be < CHUNK_SIZE (overlap={CHUNK_OVERLAP}, size={CHUNK_SIZE})"
        )

    # --- Optional: Ollama availability ---
    if os.getenv("PALI_VALIDATE_OLLAMA", "0") == "1":
        try:
            subprocess.run(["ollama", "list"], check=True, capture_output=True)
        except FileNotFoundError:
            errors.append("Ollama not found on PATH. Install it and run: ollama serve")
        except subprocess.CalledProcessError:
            errors.append("Ollama installed but not responding. Start with: ollama serve")

    if errors:
        print("❌ Configuration errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)


# Run validation only when explicitly requested.
# This avoids pytest being killed just because your DATA dir/Ollama isn't set.
if os.getenv("PALI_VALIDATE_CONFIG", "0") == "1":
    validate_config()
