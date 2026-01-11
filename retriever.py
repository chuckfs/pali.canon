# retriever.py
from typing import List, Dict
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from config import CHROMA, COLL, EMBED, TOP_K, RAG_MIN_NEEDED

def _score_bias(doc: Document, basket_hint: str | None) -> float:
    bonus = 0.0
    if basket_hint and doc.metadata.get("basket") == basket_hint:
        bonus += 0.10
    return bonus

def _dedupe_by_translation(docs: List[Document]) -> List[Document]:
    """Keep alphabetically-first by pdf_name to avoid repeating translations."""
    kept = []
    seen_names = set()
    for d in sorted(docs, key=lambda x: (x.metadata.get("pdf_name","").lower())):
        name = d.metadata.get("pdf_name", "").lower()
        if name in seen_names:
            continue
        seen_names.add(name)
        kept.append(d)
    return kept

def _client():
    emb = OllamaEmbeddings(model=EMBED)
    db = Chroma(
        collection_name=COLL,
        embedding_function=emb,
        persist_directory=CHROMA,
    )
    return db

def retrieve(plan: Dict, k: int = TOP_K) -> List[Dict]:
    db = _client()
    basket_hint = plan.get("basket_hint")
    queries = plan.get("query_terms") or []
    q = " | ".join(queries) if queries else ""

    # Phase A: true MMR (use the dedicated method)
    try:
        docs = db.max_marginal_relevance_search(q, k=k, fetch_k=k*4)
    except TypeError:
        # Older versions may use a different signature; fall back to plain search.
        docs = db.similarity_search(q, k=k)

    # If too few, widen with plain similarity
    if len(docs) < RAG_MIN_NEEDED:
        docs = db.similarity_search(q, k=k*4)

    # Soft basket bias + sort
    scored = []
    for d in docs:
        scored.append((_score_bias(d, basket_hint), d))
    scored.sort(key=lambda x: x[0], reverse=True)

    # De-dup translations and cap to k
    docs_sorted = [d for _, d in scored]
    docs_dedup = _dedupe_by_translation(docs_sorted)[:k]

    return [
        {
            "text": d.page_content,
            "pdf_name": d.metadata.get("pdf_name"),
            "page": d.metadata.get("page"),
            "span_id": d.metadata.get("span_id"),
            "relpath": d.metadata.get("relpath"), # <-- ADDED THIS LINE
            "score": 0.0,
        }
        for d in docs_dedup
    ]
