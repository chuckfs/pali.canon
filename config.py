import os
from dotenv import load_dotenv
load_dotenv()

ROOT   = os.path.expanduser(os.getenv("PALI_PROJECT_ROOT", "~/pali.canon"))
DATA   = os.path.expanduser(os.getenv("PALI_DATA_DIR", f"{ROOT}/data/pali_canon"))
CHROMA = os.path.expanduser(os.getenv("PALI_CHROMA_DIR", f"{ROOT}/chroma"))
COLL   = os.getenv("PALI_CHROMA_COLLECTION", "pali_canon")
LLM    = os.getenv("PALI_LLM_MODEL", "mistral")
EMBED  = os.getenv("PALI_EMBED_MODEL", "nomic-embed-text")
ALIAS  = os.path.expanduser(os.getenv("PALI_ALIAS_CSV", f"{ROOT}/config/aliases.csv"))
os.makedirs(CHROMA, exist_ok=True)
