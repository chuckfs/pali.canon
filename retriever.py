# retriever.py — LOCAL embeddings via Ollama, robust filters + fallback + canon-first
from __future__ import annotations
from typing import Dict, Any, List, Optional
import os, requests, chromadb

# --- config ---
CHROMA_PATH = os.path.expanduser(os.getenv("CHROMA_PATH", "~/lotus-canon/chroma"))
COLLECTION  = os.getenv("CHROMA_COLLECTION", "lotus_canon")
TOP_K       = int(os.getenv("TOP_K", "8"))
DEBUG       = os.getenv("DEBUG_RAG", "0") == "1"

# Ollama embeddings must match your indexer (you used nomic-embed-text, 768d)
OLLAMA_URL  = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")  # e.g., "nomic-embed-text"

# --- client/collection (NO embedding_function; we pass query_embeddings) ---
client = chromadb.PersistentClient(path=CHROMA_PATH)
col    = client.get_collection(name=COLLECTION)

def _dbg(*a):
    if DEBUG:
        print("[retriever]", *a)

def _ollama_embed(texts: List[str]) -> List[List[float]]:
    """Get embeddings from local Ollama (same model used at index time)."""
    vecs: List[List[float]] = []
    for t in texts:
        r = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": t},
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        v = data.get("embedding") or data.get("embeddings") or data.get("vector")
        if v is None:
            raise RuntimeError(f"Ollama embeddings returned no vector for: {t[:80]}...")
        vecs.append(v)
    return vecs

def _score_hits(h: Dict[str, Any], canonical_targets: List[str]) -> int:
    """Lightweight rank boost for exact/canonical matches in metadata."""
    m = h.get("meta", {}) or {}
    # Be liberal with keys people commonly store
    ref = " ".join(str(m.get(k, "")) for k in (
        "ref","nikaya","Nikaya","collection","book","number","sutta","sutta_no"
    )).lower()
    bonus = 0
    for ct in canonical_targets or []:
        ct_l = (ct or "").lower()
        if not ct_l:
            continue
        # match collection (SN/DN/etc.)
        if ct_l.split()[0] in ref:
            bonus += 5
        # boost numeric matches like 35.28
        for token in ct_l.split():
            if any(c.isdigit() for c in token) and token in ref:
                bonus += 10
    return bonus

def _make_filters(constraints: Dict[str, Any]) -> List[Optional[Dict[str, Any]]]:
    """
    Build a list of candidate 'where' filters. We’ll try them in order,
    then fall back to None if nothing hits.
    """
    if not constraints:
        return [None]
    out: List[Optional[Dict[str, Any]]] = []
    # If planner set nikaya=SN, try a few possible metadata keys
    target = constraints.get("nikaya")
    if target:
        for key in ("nikaya","Nikaya","collection","Collection","book","Book"):
            out.append({key: {"$eq": target}})
    # Always include a no-filter fallback at the end
    out.append(None)
    return out or [None]

def _query_once(q: str, where: Optional[Dict[str, Any]], k: int) -> Dict[str, Any]:
    if where:
        _dbg(f'query="{q}" with filter {where}')
        return col.query(query_embeddings=_ollama_embed([q]), n_results=k, where=where)
    _dbg(f'query="{q}" with NO filter')
    return col.query(query_embeddings=_ollama_embed([q]), n_results=k)

def retrieve(plan: Dict[str, Any], top_k: Optional[int] = None) -> List[Dict[str, Any]]:
    k = top_k or TOP_K
    queries: List[str] = list(plan.get("search_terms", []) or [])
    # Add canonical strings (e.g., "SN 35.28") as extra queries
    for ct in plan.get("canonical_targets", []) or []:
        if ct and ct not in queries:
            queries.append(ct)

    # Build ordered list of candidate filters; last entry is None (no filter)
    filters = _make_filters(plan.get("constraints", {}) or {})

    hits: List[Dict[str, Any]] = []
    seen = set()

    # Try each query across the candidate filters until we gather some hits
    for q in queries:
        q = (q or "").strip()
        if not q:
            continue
        got_any_for_q = False
        for filt in filters:
            try:
                res = _query_once(q, filt, k)
            except Exception as e:
                _dbg(f"query error (ignored): {e}")
                continue

            docs = res.get("documents", [[]])[0]
            if not docs:
                # Try next filter (or fallback to no filter)
                continue

            metas = res.get("metadatas", [[]])[0]
            ids   = res.get("ids", [[]])[0]
            for i, doc in enumerate(docs):
                meta = metas[i] if i < len(metas) else {}
                cid  = ids[i]   if i < len(ids)   else ""
                key = (cid, meta.get("page"), meta.get("source"))
                if key in seen:
                    continue
                seen.add(key)
                hits.append({"id": cid, "text": doc, "meta": meta})
            got_any_for_q = True
            break  # stop cycling filters for this q once we got results

        if not got_any_for_q:
            _dbg(f'no results for "{q}" under any filter')

    # Re-rank to push exact canonical refs up
    ctargets = [t for t in (plan.get("canonical_targets") or [])]
    hits.sort(key=lambda h: _score_hits(h, ctargets), reverse=True)

    # Canon-first: if any meta clearly contains the target number (e.g., 35.28), surface them
    canon_hits = []
    other_hits = []
    needle = None
    for ct in ctargets:
        for token in ct.split():
            if any(c.isdigit() for c in token):
                needle = token
                break
        if needle:
            break
    if needle:
        for h in hits:
            if needle in str(h.get("meta", {})).replace(" ", ""):
                canon_hits.append(h)
            else:
                other_hits.append(h)
        hits = canon_hits + other_hits

    final = hits[:k]
    _dbg(f"final hits: {len(final)}")
    return final