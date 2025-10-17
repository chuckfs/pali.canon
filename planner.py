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
import re, unicodedata, os, json
from pathlib import Path
from typing import Dict, Any, List
from alias_loader import load_aliases, fuzzy_ids, _strip_diacritics

try:
    from langchain_ollama import ChatOllama
except Exception:
    ChatOllama = None

# Load aliases from external files (set LOTUS_ALIAS_CSV / LOTUS_ALIAS_YAML)
ID_TO_ALIASES, ALIAS_TO_ID = load_aliases()

SUTTA_ID_RE = re.compile(
    r'\b(?:(DN|MN|SN|AN|KN|Sn|Khp|Dhp|Thag|Thig)\s*[-\s\.:]?\s*\d+(?:\.\d+)?)\b',
    re.IGNORECASE
)

# Environment toggles for optional LLM rewriter
LOTUS_USE_PLANNER_LLM = os.getenv("LOTUS_USE_PLANNER_LLM", "0") == "1"
PLANNER_LLM_MODEL = os.getenv("PLANNER_LLM_MODEL", os.getenv("LOTUS_LLM_MODEL", "mistral"))
PLANNER_LLM_CACHE_PATH = os.getenv("LOTUS_LLM_REWRITE_CACHE", 
                                    os.path.expanduser("~/PaLi-CANON/llm_rewrite_cache.json"))

def _load_llm_cache() -> Dict[str, Dict[str, Any]]:
    """Load LLM cache from JSON file."""
    cache_path = Path(PLANNER_LLM_CACHE_PATH)
    if cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_llm_cache(cache: Dict[str, Dict[str, Any]]) -> None:
    """Save LLM cache to JSON file."""
    cache_path = Path(PLANNER_LLM_CACHE_PATH)
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def _llm_expand_query(question: str) -> Dict[str, Any]:
    """
    Use LLM to expand query with canonical IDs and search terms.
    Conservative behavior: if LOTUS_USE_PLANNER_LLM=0, immediately return {}.
    
    Returns dict with keys: search_terms (list), canonical_ids (list), nikaya (str), basket (str)
    Falls back to {} on any error.
    """
    if not LOTUS_USE_PLANNER_LLM:
        return {}
    
    if not ChatOllama:
        return {}
    
    # Normalize question for cache key
    cache_key = question.strip().lower()
    
    # Check cache
    cache = _load_llm_cache()
    if cache_key in cache:
        return cache.get(cache_key, {})
    
    try:
        # Create LLM with strict JSON-only prompt
        llm = ChatOllama(model=PLANNER_LLM_MODEL, temperature=0)
        
        prompt = f"""You are a Pali Canon expert. Extract search information from this question.
Return ONLY a JSON object (no other text) with these allowed keys:
- "search_terms": list of search terms
- "canonical_ids": list of canonical sutta IDs like "SN 35.28", "MN 22", "DN 31"
- "nikaya": one of DN, MN, SN, AN, KN (or empty)
- "basket": one of sutta, vinaya, abhidhamma (or empty)

Question: {question}

JSON:"""
        
        response = llm.invoke(prompt)
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        # Extract first JSON object from response
        start = response_text.find('{')
        end = response_text.rfind('}')
        if start >= 0 and end > start:
            json_str = response_text[start:end+1]
            parsed = json.loads(json_str)
            
            # Enforce allowed keys
            allowed_keys = {"search_terms", "canonical_ids", "nikaya", "basket"}
            result = {k: v for k, v in parsed.items() if k in allowed_keys}
            
            # Validate types
            if "search_terms" in result and not isinstance(result["search_terms"], list):
                result["search_terms"] = [str(result["search_terms"])] if result["search_terms"] else []
            if "canonical_ids" in result and not isinstance(result["canonical_ids"], list):
                result["canonical_ids"] = [str(result["canonical_ids"])] if result["canonical_ids"] else []
            
            # Cache the result
            cache[cache_key] = result
            _save_llm_cache(cache)
            
            return result
        
    except Exception:
        pass
    
    return {}

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