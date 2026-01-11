# retriever.py
import os
import pickle
from typing import List, Dict, Optional
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder
from rank_bm25 import BM25Okapi
from config import CHROMA, COLL, EMBED, TOP_K, RAG_MIN_NEEDED

# Cache paths
BM25_CACHE = os.path.join(CHROMA, "bm25_cache.pkl")

# Lazy-loaded globals
_reranker = None
_bm25_index = None
_bm25_docs = None

def _get_reranker():
    global _reranker
    if _reranker is None:
        print("Loading cross-encoder reranker...")
        _reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    return _reranker

def _tokenize(text: str) -> List[str]:
    """Simple whitespace tokenizer with lowercasing."""
    return text.lower().split()

def _build_bm25_index(db) -> tuple:
    """Build BM25 index from all documents in the vector store."""
    print("Building BM25 index (first run only)...")
    
    collection = db._collection
    results = collection.get(include=["documents", "metadatas"])
    
    documents = results.get("documents", [])
    metadatas = results.get("metadatas", [])
    
    docs = []
    for i, (text, meta) in enumerate(zip(documents, metadatas)):
        if text:
            docs.append(Document(page_content=text, metadata=meta or {}))
    
    tokenized = [_tokenize(d.page_content) for d in docs]
    bm25 = BM25Okapi(tokenized)
    
    with open(BM25_CACHE, 'wb') as f:
        pickle.dump((bm25, docs), f)
    
    print(f"  ✓ BM25 index built with {len(docs)} documents")
    return bm25, docs

def _get_bm25_index(db):
    """Get or build BM25 index."""
    global _bm25_index, _bm25_docs
    
    if _bm25_index is not None:
        return _bm25_index, _bm25_docs
    
    if os.path.exists(BM25_CACHE):
        try:
            with open(BM25_CACHE, 'rb') as f:
                _bm25_index, _bm25_docs = pickle.load(f)
            print(f"Loaded BM25 index from cache ({len(_bm25_docs)} docs)")
            return _bm25_index, _bm25_docs
        except Exception as e:
            print(f"  ⚠️ Failed to load BM25 cache: {e}")
    
    _bm25_index, _bm25_docs = _build_bm25_index(db)
    return _bm25_index, _bm25_docs

def _bm25_search(query: str, db, k: int = 20) -> List[Document]:
    """Search using BM25."""
    bm25, docs = _get_bm25_index(db)
    
    tokenized_query = _tokenize(query)
    scores = bm25.get_scores(tokenized_query)
    
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
    
    return [docs[i] for i in top_indices if scores[i] > 0]

def _citation_search(target_refs: List[str], db) -> List[Document]:
    """Search for documents containing specific citation references."""
    if not target_refs:
        return []
    
    bm25, docs = _get_bm25_index(db)
    
    matching_docs = []
    for doc in docs:
        doc_citations = doc.metadata.get("citations", "")
        if doc_citations:
            for ref in target_refs:
                # Normalize for comparison
                ref_normalized = ref.upper().replace(" ", "")
                citations_normalized = doc_citations.upper().replace(" ", "")
                if ref_normalized in citations_normalized:
                    matching_docs.append(doc)
                    break
    
    return matching_docs

def _reciprocal_rank_fusion(results_lists: List[List[Document]], k: int = 60) -> List[Document]:
    """Combine multiple ranked lists using Reciprocal Rank Fusion."""
    doc_scores = {}
    doc_objects = {}
    
    for results in results_lists:
        for rank, doc in enumerate(results):
            key = doc.page_content[:200]
            
            if key not in doc_objects:
                doc_objects[key] = doc
            
            rrf_score = 1.0 / (k + rank + 1)
            doc_scores[key] = doc_scores.get(key, 0) + rrf_score
    
    sorted_keys = sorted(doc_scores.keys(), key=lambda x: doc_scores[x], reverse=True)
    
    return [doc_objects[key] for key in sorted_keys]

def _rerank(query: str, docs: List[Document], top_n: int) -> List[Document]:
    """Rerank documents using cross-encoder."""
    if not docs:
        return docs
    
    reranker = _get_reranker()
    pairs = [(query, d.page_content) for d in docs]
    scores = reranker.predict(pairs)
    
    scored_docs = list(zip(scores, docs))
    scored_docs.sort(key=lambda x: x[0], reverse=True)
    
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
    target_refs = plan.get("targets", [])  # Citation targets from planner
    queries = plan.get("query_terms") or []
    q = " | ".join(queries) if queries else ""
    original_query = queries[0] if queries else q

    # Build filter for basket if specified
    where_filter = None
    if basket_hint:
        where_filter = {"basket": basket_hint}

    fetch_k = k * 4

    # === HYBRID SEARCH ===
    
    # 1. Citation-based search (highest priority if targets specified)
    citation_docs = _citation_search(target_refs, db) if target_refs else []
    
    # 2. Semantic search (vector)
    try:
        if where_filter:
            semantic_docs = db.max_marginal_relevance_search(q, k=fetch_k, fetch_k=fetch_k*2, filter=where_filter)
        else:
            semantic_docs = db.max_marginal_relevance_search(q, k=fetch_k, fetch_k=fetch_k*2)
    except TypeError:
        if where_filter:
            semantic_docs = db.similarity_search(q, k=fetch_k, filter=where_filter)
        else:
            semantic_docs = db.similarity_search(q, k=fetch_k)

    # 3. BM25 keyword search
    bm25_docs = _bm25_search(original_query, db, k=fetch_k)

    # 4. Combine with Reciprocal Rank Fusion
    # Citation docs get extra weight by appearing in their own list
    all_result_lists = [semantic_docs, bm25_docs]
    if citation_docs:
        # Add citation docs twice to boost their score
        all_result_lists.insert(0, citation_docs)
        all_result_lists.insert(0, citation_docs)
    
    docs = _reciprocal_rank_fusion(all_result_lists)[:fetch_k]

    # If too few results with filter, try without filter
    if len(docs) < RAG_MIN_NEEDED and where_filter:
        try:
            semantic_docs = db.max_marginal_relevance_search(q, k=fetch_k, fetch_k=fetch_k*2)
        except TypeError:
            semantic_docs = db.similarity_search(q, k=fetch_k)
        bm25_docs = _bm25_search(original_query, db, k=fetch_k)
        
        all_result_lists = [semantic_docs, bm25_docs]
        if citation_docs:
            all_result_lists.insert(0, citation_docs)
            all_result_lists.insert(0, citation_docs)
        
        docs = _reciprocal_rank_fusion(all_result_lists)[:fetch_k]

    # === RERANKING ===
    if docs:
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
            "nikaya": d.metadata.get("nikaya", ""),
            "citations": d.metadata.get("citations", ""),
            "score": 0.0,
        }
        for d in docs_dedup
    ]

def rebuild_bm25_index():
    """Utility function to rebuild BM25 index after reindexing."""
    global _bm25_index, _bm25_docs
    
    if os.path.exists(BM25_CACHE):
        os.remove(BM25_CACHE)
    
    _bm25_index = None
    _bm25_docs = None
    
    db = _client()
    _get_bm25_index(db)
    print("BM25 index rebuilt.")

if __name__ == "__main__":
    rebuild_bm25_index()
