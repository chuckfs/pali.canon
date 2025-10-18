# planner.py
import os, re, csv
from typing import Dict, List, Optional
from rapidfuzz import fuzz, process
from config import ALIAS

ID_RE = re.compile(r"\b([DMAS]N)\s*[- ]?\s*(\d{1,3})(?:[\. ]\s*(\d{1,3}))?\b", re.I)

def _load_aliases(path: str) -> Dict[str, str]:
    table = {}
    if not path or not os.path.exists(path):
        return table
    with open(path, newline='', encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cid = row.get("canonical_id", "").strip()
            alias = row.get("alias", "").strip()
            if cid and alias:
                table[alias.lower()] = cid
    return table

ALIASES = _load_aliases(ALIAS)
ALIAS_KEYS = list(ALIASES.keys())

def _extract_ids(q: str) -> List[str]:
    out = []
    for m in ID_RE.finditer(q):
        nik = m.group(1).upper()
        a = m.group(2)
        b = m.group(3)
        cid = f"{nik} {a}.{b}" if b else f"{nik} {a}"
        out.append(cid)
    return list(dict.fromkeys(out))

def _basket_hint(q: str) -> Optional[str]:
    ql = q.lower()
    if "vinaya" in ql: return "vinaya"
    if "abhidhamma" in ql or "abhi" in ql: return "abhidhamma"
    return "sutta" if any(w in ql for w in ["sutta","sutta nipāta","khp","dhp","thig","thag"]) else None

def _alias_targets(q: str) -> List[str]:
    if not ALIAS_KEYS:
        return []
    # try to map short nicknames like "fire sermon" → "SN 35.28"
    matches = process.extract(q.lower(), ALIAS_KEYS, scorer=fuzz.WRatio, limit=5)
    targets = []
    for alias, score, _ in matches:
        if score >= 85:
            targets.append(ALIASES[alias])
    return list(dict.fromkeys(targets))

def plan(query: str) -> dict:
    targets = _extract_ids(query)
    targets += [t for t in _alias_targets(query) if t not in targets]
    bhint = _basket_hint(query)
    # query_terms feed retriever directly
    query_terms = [query]
    if targets: query_terms += targets
    return {
        "targets": targets,
        "basket_hint": bhint,
        "query_terms": list(dict.fromkeys(query_terms))
    }

if __name__ == "__main__":
    import sys, json
    print(json.dumps(plan("What is the Fire Sermon (Ādittapariyāya)? SN 35.28"), indent=2))