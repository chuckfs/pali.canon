# retriever.py
from typing import List, Dict
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder
from config import CHROMA, COLL, EMBED, TOP_K, RAG_MIN_NEEDED

# Load cross-encoder for reranking (loaded once at module level)
_reranker = None

def _get_reranker():
    global _reranker
    if _reranker is None:
        print("Loading cross-encoder reranker...")
        _reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    return _reranker

def _rerank(query: str, docs: List[Document], top_n: int) -> List[Document]:
    """Rerank documents using cross-encoder."""
    if not docs:
        return docs
    
    reranker = _get_reranker()
    
    # Create query-document pairs
    pairs = [(query, d.page_content) for d in docs]
    
    # Score all pairs
    scores = reranker.predict(pairs)
    
    # Sort by score descending
    scored_docs = list(zip(scores, docs))
    scored_docs.sort(key=lambda x: x[0], reverse=True)
    
    # Return top_n
    return [doc for _, doc in scored_docs[:top_n]]

def _score_bias(doc: Document, basket_hint: str | None) -> float:
    bonus = 0.0
    if basket_hint and doc.metadata.get("basket") == basket_hint:
        bonus += 0.10
    return bonus

def _dedupe_by_translation(docs: List[Document]) -> List[Document]:
    """Keep alphabetically-first by pdf_name to avoid repeating translations."""
    kept = []
    seen_names = set()
    for d in sorted(docs, key=lambda x: (x.metadata.get("pdf_name", "").lower())):
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

    # Build filter for basket if specified
    where_filter = None
    if basket_hint:
        where_filter = {"basket": basket_hint}

    # Phase A: Get more candidates than needed for reranking
    fetch_k = k * 4  # Fetch extra for reranking
    
    try:
        if where_filter:
            docs = db.max_marginal_relevance_search(q, k=fetch_k, fetch_k=fetch_k*2, filter=where_filter)
        else:
            docs = db.max_marginal_relevance_search(q, k=fetch_k, fetch_k=fetch_k*2)
    except TypeError:
        if where_filter:
            docs = db.similarity_search(q, k=fetch_k, filter=where_filter)
        else:
            docs = db.similarity_search(q, k=fetch_k)

    # If too few results with filter, try without filter
    if len(docs) < RAG_MIN_NEEDED and where_filter:
        try:
            docs = db.max_marginal_relevance_search(q, k=fetch_k, fetch_k=fetch_k*2)
        except TypeError:
            docs = db.similarity_search(q, k=fetch_k)

    # If still too few, widen search
    if len(docs) < RAG_MIN_NEEDED:
        docs = db.similarity_search(q, k=fetch_k*2)

    # Phase B: Rerank using cross-encoder
    if docs:
        # Use original query for reranking (not the joined version)
        original_query = queries[0] if queries else q
        docs = _rerank(original_query, docs, top_n=k*2)

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
            "relpath": d.metadata.get("relpath"),
            "score": 0.0,
        }
        for d in docs_dedup
    ]
```

**What this does:**

1. **Fetches more candidates** — Gets `k * 4` documents from vector search instead of just `k`
2. **Reranks with cross-encoder** — Uses `ms-marco-MiniLM-L-6-v2` to score query-document relevance
3. **Lazy loading** — Reranker model only loads on first use
4. **Uses original query** — Reranks with the human's actual question, not the processed version

**The flow is now:**
```
Query → Vector Search (get 32 candidates) → Cross-Encoder Rerank (keep top 16) → Basket Bias → Dedupe → Return top 8
