#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Retriever: Two-phase vector search (filtered → fallback) + hybrid ranking (vector + BM25),
plus a gentle, generic re-rank using planner targets/aliases.

Env:
  RAG_MIN_NEEDED   -> int, if Phase A yields < this many, do Phase B (default 4)
  TOP_K            -> default top_k (fallback if CLI/GUI not provided)
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
import os, json

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

# Optional BM25 (pip install rank_bm25)
try:
    from rank_bm25 import BM25Okapi
except Exception:
    BM25Okapi = None

PERSIST_DIR = os.getenv("LOTUS_CHROMA_DIR", os.path.expanduser("~/PaLi-CANON/chroma"))
COLLECTION  = os.getenv("LOTUS_CHROMA_COLLECTION", "pali_canon")
EMBED_MODEL = os.getenv("LOTUS_EMBED_MODEL", "nomic-embed-text")
TOP_K       = int(os.getenv("TOP_K", "8"))
DEBUG       = os.getenv("DEBUG_RAG", "0") == "1"
MIN_NEEDED  = int(os.getenv("RAG_MIN_NEEDED", "4"))

ENV_BASKET  = (os.getenv("RAG_BASKET") or "").strip().lower()

NIKAYA_MAP = {
    "DN": "digha_nikaya",
    "MN": "majjhima_nikaya",
    "SN": "samyutta_nikaya",
    "AN": "anguttara_nikaya",
    "KN": "khuddaka_nikaya",
}
BASKET_MAP = {
    "sutta": "sutta_pitaka",
    "vinaya": "vinaya_pitaka",
    "abhidhamma": "abhidhamma_pitaka",
}

def _dbg(*a):
    if DEBUG:
        print("[retriever]", *a)

def _build_db() -> Chroma:
    emb = OllamaEmbeddings(model=EMBED_MODEL)
    return Chroma(collection_name=COLLECTION, persist_directory=PERSIST_DIR, embedding_function=emb)

def _filter_from_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    clauses: List[Dict[str, Any]] = [{"tier": {"$eq": "canon"}}]
    constraints = plan.get("constraints") or {}
    nikaya_code = (constraints.get("nikaya") or "").strip().upper() or None
    basket_key  = (constraints.get("basket") or "").strip().lower() or None

    if ENV_BASKET:
        basket_key = ENV_BASKET
    if nikaya_code in NIKAYA_MAP and not basket_key:
        basket_key = "sutta"

    if basket_key in BASKET_MAP:
        clauses.append({"basket": {"$eq": BASKET_MAP[basket_key]}})
    if nikaya_code in NIKAYA_MAP:
        clauses.append({"nikaya": {"$in": [NIKAYA_MAP[nikaya_code]]}})

    filt = clauses[0] if len(clauses) == 1 else {"$and": clauses}
    _dbg("filter:", json.dumps(filt, ensure_ascii=False))
    return filt

def _bm25_scores(query: str, docs: List[Dict[str, Any]], k: int = 8) -> List[Tuple[int, float]]:
    if not BM25Okapi or not docs:
        return []
    corpus = [d["text"].split() for d in docs]
    bm = BM25Okapi(corpus)
    scores = bm.get_scores(query.split())
    ranked = sorted(list(enumerate(scores)), key=lambda x: x[1], reverse=True)[:k]
    return ranked

def _to_hits(results: List[Tuple[Any, float]], k: int) -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []
    for doc, score in results:
        meta = dict(doc.metadata or {})
        page = meta.get("page", None)
        rel  = meta.get("relpath", meta.get("source", meta.get("filename", "")))
        hits.append({
            "text": doc.page_content,
            "score": float(score),
            "meta": {**meta, "citation": f"{rel}" + (f" p.{page+1}" if isinstance(page, int) else "")},
        })
    hits.sort(key=lambda h: h["score"], reverse=True)
    return hits[:k]

def retrieve(plan: Dict[str, Any], top_k: Optional[int] = None) -> List[Dict[str, Any]]:
    k = top_k or TOP_K
    query = plan.get("query") or " ".join(plan.get("search_terms", [])) or ""
    if not query:
        raise ValueError("No query text available (plan.query / plan.search_terms empty).")

    db = _build_db()
    filt = _filter_from_plan(plan)

    # Phase A: filtered vector (oversample)
    vecA = db.similarity_search_with_relevance_scores(query, k=max(k, 10), filter=filt)
    poolA = _to_hits(vecA, k=10*k)

    # Phase B: broaden if needed (tier-only)
    poolB: List[Dict[str, Any]] = []
    if len(poolA) < MIN_NEEDED:
        broad = {"tier": {"$eq": "canon"}}
        vecB = db.similarity_search_with_relevance_scores(query, k=max(k, 10), filter=broad)
        poolB = _to_hits(vecB, k=10*k)

    pool = poolA + poolB

    # Hybrid: small BM25 bump
    bm = _bm25_scores(query, pool, k=5*k)
    bm_boost = {idx: sc for idx, sc in bm}
    if pool:
        smax = max(h["score"] for h in pool) or 1.0
    else:
        smax = 1.0
    for i, h in enumerate(pool):
        base = h["score"] / smax
        extra = bm_boost.get(i, 0.0)
        h["hybrid_score"] = base + 0.1 * extra

    # Gentle, generic rerank using canonical targets + alias terms
    targets = [t.replace(" ", "").lower() for t in (plan.get("canonical_targets") or [])]
    alias_terms = [t.strip().lower() for t in plan.get("search_terms", [])[:8]]

    def _final_score(h):
        s = h.get("hybrid_score", h["score"])
        text_l = h["text"].lower()
        meta_l = json.dumps(h.get("meta", {}), ensure_ascii=False).lower()
        if any(t in text_l or t in meta_l for t in targets): s += 0.15
        if any(a and a in text_l for a in alias_terms):      s += 0.05
        return s

    pool.sort(key=_final_score, reverse=True)
    out = pool[:k]
    _dbg(f"final hits: {len(out)}")
    return out