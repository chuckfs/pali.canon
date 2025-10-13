# planner.py — Stage 1: Generative "query planner" (local Mistral via Ollama)
# - Resolves user phrasing to canonical targets (e.g., "fire sermon" -> "SN 35.28")
# - Produces structured search terms + optional constraints for the retriever
# - Stays 100% local (uses models_local.llm)

from __future__ import annotations
import json, csv, os
from typing import Dict, Any, List
from models_local import llm

# Optional CSV: alias -> canonical mapping (two columns: alias, canonical)
CANON_MAP_CSV = os.path.expanduser("~/lotus-canon/canon_map.csv")

# Built-in aliases (lowercased)
BUILTIN_ALIASES = {
    "fire sermon": "SN 35.28",
    "fire discourse": "SN 35.28",
    "adittapariyaya": "SN 35.28",
    "ādittapariyāya": "SN 35.28",
    "first sermon": "SN 56.11",            # Dhammacakkappavattana
    "second sermon": "SN 22.59",           # Anattalakkhaṇa
    "last sermon": "DN 16",                # Mahāparinibbāna
    "parinibbana": "DN 16",
}

def _load_csv_aliases() -> Dict[str, str]:
    out = {}
    if os.path.exists(CANON_MAP_CSV):
        try:
            with open(CANON_MAP_CSV, newline='', encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    alias = (row.get("alias") or "").strip().lower()
                    canon = (row.get("canonical") or "").strip()
                    if alias and canon:
                        out[alias] = canon
        except Exception:
            pass
    return out

CSV_ALIASES = _load_csv_aliases()

def _alias_seed(question: str) -> List[str]:
    q = " ".join((question or "").lower().split())
    cands: List[str] = []
    # CSV overrides first
    for a, canon in CSV_ALIASES.items():
        if a in q and canon not in cands:
            cands.append(canon)
    # Then built-ins
    for a, canon in BUILTIN_ALIASES.items():
        if a in q and canon not in cands:
            cands.append(canon)
    return cands

SYSTEM = """You are a query planner for a Buddhist Canon assistant.
Return ONLY compact JSON with keys:
- canonical_targets: array of canonical identifiers (e.g., "SN 35.28")
- search_terms: array of precise strings for semantic search (no citations here)
- constraints: optional dict of filters, e.g., {"nikaya": "SN"}
- require_citations: true

Rules:
- If user refers to Fire Sermon / Fire Discourse / Ādittapariyāya, prefer "SN 35.28".
- Avoid hallucinating identifiers; if unsure, leave canonical_targets empty.
- search_terms must be useful to a vector search (add synonyms, Pāli spellings).
- Keep JSON small and valid; no commentary outside JSON.
"""

PROMPT_TMPL = """User question:
{question}

You may refine this seed (it comes from alias heuristics):
{seed}
"""

def plan_query(question: str) -> Dict[str, Any]:
    # Build a safe seed first (alias pass + smart constraint for Fire Sermon)
    seed = {
        "canonical_targets": _alias_seed(question),
        "search_terms": [question],
        "constraints": {},
        "require_citations": True,
    }

    # If it's clearly Fire Sermon, bias retrieval to SN to avoid DN16 confusion
    ql = (question or "").lower()
    if any(k in ql for k in ["fire sermon", "fire discourse", "adittapariyaya", "ādittapariyāya"]):
        seed["constraints"]["nikaya"] = "SN"

    prompt = PROMPT_TMPL.format(question=question, seed=json.dumps(seed))
    out = llm(prompt, system=SYSTEM, temperature=0.0)

    # Parse LLM JSON; on error, fall back to seed
    try:
        obj = json.loads(out)
        if not isinstance(obj, dict):
            raise ValueError("Planner did not return a JSON object.")
    except Exception:
        obj = {}

    # Merge / ensure defaults
    obj.setdefault("canonical_targets", seed["canonical_targets"])
    obj.setdefault("search_terms", seed["search_terms"])
    obj.setdefault("constraints", seed["constraints"])
    obj.setdefault("require_citations", True)

    # Deduplicate terms while preserving order
    def _dedup(seq: List[str]) -> List[str]:
        seen = set(); out = []
        for s in seq or []:
            if s and s not in seen:
                seen.add(s); out.append(s)
        return out

    obj["canonical_targets"] = _dedup(obj.get("canonical_targets", []))
    obj["search_terms"] = _dedup(obj.get("search_terms", []))

    return obj