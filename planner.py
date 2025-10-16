#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Planner: parse the user question into a plan with constraints and targets.

- Extract IDs like 'SN 35.28', 'MN22', 'DN-31' (normalized to 'SN 35.28', 'MN 22', etc.).
- Load data-driven aliases from CSV/YAML + fuzzy match (see alias_loader.py).
- Infer Nikāya from IDs (SN/MN/DN/AN; Sn/Khp/Dhp/Thag/Thig → KN umbrella).
- Gentle basket inference (vinaya/abhidhamma/“sutta” words).
- Seed search_terms with alias/ID expansions from your data, + diacritic-stripped user query.
"""
from __future__ import annotations
import re, unicodedata
from typing import Dict, Any, List
from alias_loader import load_aliases, fuzzy_ids, _strip_diacritics

# Load aliases from external files (set LOTUS_ALIAS_CSV / LOTUS_ALIAS_YAML)
ID_TO_ALIASES, ALIAS_TO_ID = load_aliases()

SUTTA_ID_RE = re.compile(
    r'\b(?:(DN|MN|SN|AN|KN|Sn|Khp|Dhp|Thag|Thig)\s*[-\s\.:]?\s*\d+(?:\.\d+)?)\b',
    re.IGNORECASE
)

def _norm_id(token: str) -> str:
    t = token.upper().replace(" ", "")
    t = t.replace(":", ".").replace("-", "")
    code = t[:2]
    rest = t[2:]
    if rest and rest[0].isdigit():
        rest = " " + rest
    return f"{code}{rest}"

def _scan_ids(q: str) -> List[str]:
    seen, out = set(), []
    for m in SUTTA_ID_RE.finditer(q):
        nid = _norm_id(m.group(0))
        if nid not in seen:
            out.append(nid); seen.add(nid)
    return out

def plan_query(q: str) -> Dict[str, Any]:
    q_stripped = (q or "").strip()
    plan: Dict[str, Any] = {
        "original": q_stripped,
        "query": q_stripped,
        "search_terms": [],
        "constraints": {},
        "canonical_targets": [],
        "require_citations": True,
    }

    # 1) Direct IDs
    ids = _scan_ids(q_stripped)

    # 2) Aliases (exact + fuzzy) from external data
    alias_ids = []
    # exact / normalized lookups
    q_lc = q_stripped.lower()
    q_plain = _strip_diacritics(q_lc)
    for key, cid in ALIAS_TO_ID.items():
        if key in q_lc or key in q_plain:
            if cid not in alias_ids:
                alias_ids.append(cid)
    # fuzzy (threshold can be tuned via ALIAS_FUZZY_THRESHOLD)
    from os import getenv
    fuzzy_thresh = int(getenv("ALIAS_FUZZY_THRESHOLD", "85"))
    for cid in fuzzy_ids(q_stripped, ALIAS_TO_ID, top_n=3, threshold=fuzzy_thresh):
        if cid not in alias_ids:
            alias_ids.append(cid)

    for cid in alias_ids:
        if cid not in ids:
            ids.append(cid)

    if ids:
        plan["canonical_targets"] = ids
        head = ids[0]
        code = head.split()[0]  # e.g. "SN", "MN", "DN", "AN", "Sn", "Khp", "Dhp", "Thag", "Thig"
        # Khuddaka umbrella
        if code in {"Sn", "Khp", "Dhp", "Thag", "Thig"}:
            plan["constraints"]["nikaya"] = "KN"
        elif code in {"SN","MN","DN","AN","KN"}:
            plan["constraints"]["nikaya"] = code
        elif code.lower() in {"sn","mn","dn","an","kn"}:
            plan["constraints"]["nikaya"] = code.upper()

    # 3) Basket inference (gentle)
    if "vinaya" in q_lc:
        plan["constraints"]["basket"] = "vinaya"
    elif any(x in q_lc for x in ["abhidhamma", "paṭṭhāna", "patthana", "dhammasaṅgaṇī", "dhammasangani"]):
        plan["constraints"]["basket"] = "abhidhamma"
    elif any(x in q_lc for x in ["sutta", "sūtta", "sermon", "discourse"]):
        plan["constraints"].setdefault("basket", "sutta")

    # 4) Seed search terms: user text (+plain) + all aliases we know for detected IDs
    seeds = [q_stripped]
    if q_plain != q_lc:
        seeds.append(_strip_diacritics(q_stripped))
    for sid in ids:
        for a in ID_TO_ALIASES.get(sid, []):
            if a not in seeds:
                seeds.append(a)
    plan["search_terms"] = seeds

    return plan