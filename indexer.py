# indexer.py
import os
import re
import shutil
import subprocess
from typing import List

import fitz  # PyMuPDF
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma          # modern import
from langchain_core.documents import Document

from config import DATA, CHROMA, COLL, EMBED, CHUNK_SIZE, CHUNK_OVERLAP

# OCR cache mirrors the data tree so we don't re-OCR on every run
OCR_CACHE = os.path.join(os.path.dirname(DATA), "ocr_cache")

# Sentence-ish splitter (lightweight; handles A/Pāli capitals too)
_SPLIT_RE = re.compile(r"(?<=[\.!?])\s+(?=[A-ZĀĪŪṄÑṬḌḶ])")

# Hard limit for chunk size (nomic-embed-text has 8192 token limit, ~4 chars per token)
MAX_CHUNK_CHARS = 6000

def _has_text(pdf_path: str) -> bool:
    """Check if the PDF has a usable text layer (not just cover pages)."""
    try:
        with fitz.open(pdf_path) as doc:
            # Check pages deeper in the document, not just the beginning
            # Google Books PDFs have text on cover pages but scanned content
            pages_to_check = [0, 1, 2]  # First 3 pages
            
            # Also check some pages in the middle of the document
            if len(doc) > 20:
                pages_to_check.extend([10, 20, len(doc) // 2])
            
            text_pages = 0
            for p in pages_to_check:
                if p < len(doc):
                    text = doc[p].get_text("text").strip()
                    # Must have substantial text, not just a few characters
                    if len(text) > 200:
                        text_pages += 1
            
            # Need text on most checked pages to consider it text-based
            return text_pages >= len(pages_to_check) * 0.6
    except Exception:
        return False

def _ensure_ocr(pdf_path: str) -> str:
    """
    If the PDF lacks a text layer, run OCRmyPDF once into OCR_CACHE.
    If it has text, mirror-copy it into OCR_CACHE to unify read path.
    """
    os.makedirs(OCR_CACHE, exist_ok=True)
    rel = os.path.relpath(pdf_path, DATA)
    out_pdf = os.path.join(OCR_CACHE, rel)
    os.makedirs(os.path.dirname(out_pdf), exist_ok=True)

    if os.path.exists(out_pdf):
        return out_pdf

    if _has_text(pdf_path):
        shutil.copyfile(pdf_path, out_pdf)
        return out_pdf

    # OCR required
    print(f"    🔍 Starting OCR (this may take several minutes)...")
    tmp = out_pdf + ".tmp.pdf"
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    cmd = ["ocrmypdf", "--quiet", "--force-ocr", "--output-type", "pdf", pdf_path, tmp]
    subprocess.run(cmd, check=True)
    shutil.move(tmp, out_pdf)
    print(f"    ✓ OCR complete")
    return out_pdf

def _iter_pdfs(root: str):
    for dirpath, _, files in os.walk(root):
        for f in files:
            if f.lower().endswith(".pdf"):
                yield os.path.join(dirpath, f)

def _split_sentences(text: str) -> List[str]:
    parts = _SPLIT_RE.split(text.strip())
    return [p.strip() for p in parts if p.strip()]

def _chunk_sentences(sents: List[str], max_len=CHUNK_SIZE, overlap=CHUNK_OVERLAP) -> List[str]:
    chunks, buf = [], []
    cur_len = 0
    for s in sents:
        if cur_len + len(s) + 1 > max_len and buf:
            chunks.append(" ".join(buf).strip())
            # create overlap window
            joined = " ".join(buf)
            if len(joined) > overlap:
                while buf and len(" ".join(buf)) > overlap:
                    buf.pop(0)
            else:
                buf = []
            cur_len = len(" ".join(buf))
        buf.append(s)
        cur_len += len(s) + 1
    if buf:
        chunks.append(" ".join(buf).strip())
    return chunks

def _truncate_chunk(text: str, max_chars: int = MAX_CHUNK_CHARS) -> str:
    """Truncate chunk if it exceeds max length."""
    if len(text) <= max_chars:
        return text
    # Truncate at word boundary
    truncated = text[:max_chars].rsplit(' ', 1)[0]
    return truncated

def _basket_from_path(path: str) -> str:
    low = path.lower()
    if "/vinaya" in low:
        return "vinaya"
    if "/abhidhamma" in low or "/abhi" in low:
        return "abhidhamma"
    return "sutta"

def _add_documents_safely(vectordb, docs: List[Document]):
    """Add documents one at a time if batch fails."""
    try:
        vectordb.add_documents(docs)
    except Exception as e:
        if "context length" in str(e).lower() or "input length" in str(e).lower():
            # Fall back to one-by-one
            print(f"    ⚠️ Batch failed, adding one-by-one...")
            for doc in docs:
                try:
                    vectordb.add_documents([doc])
                except Exception as e2:
                    print(f"    ❌ Skipped chunk (too long): {len(doc.page_content)} chars")
        else:
            raise e

def build_index(data_dir=DATA, persist_dir=CHROMA, collection=COLL):
    os.makedirs(persist_dir, exist_ok=True)

    # Count PDFs first
    pdf_list = list(_iter_pdfs(data_dir))
    total_pdfs = len(pdf_list)
    
    if total_pdfs == 0:
        print(f"ERROR: No PDFs found in {data_dir}")
        return
    
    print("="*70)
    print("INDEXING PALI CANON")
    print("="*70)
    print(f"Source directory: {data_dir}")
    print(f"Vector store: {persist_dir}")
    print(f"PDFs found: {total_pdfs}")
    print(f"Chunk size: {CHUNK_SIZE} chars, overlap: {CHUNK_OVERLAP} chars")
    print("="*70)

    embeddings = OllamaEmbeddings(model=EMBED)
    vectordb = Chroma(
        collection_name=collection,
        embedding_function=embeddings,
        persist_directory=persist_dir,
    )

    docs: List[Document] = []
    total_chunks = 0
    skipped_chunks = 0
    ocr_count = 0
    
    for pdf_idx, src_pdf in enumerate(pdf_list, 1):
        pdf_name = os.path.basename(src_pdf)
        print(f"\n[{pdf_idx}/{total_pdfs}] {pdf_name}")
        
        # OCR check
        needs_ocr = not _has_text(src_pdf)
        if needs_ocr:
            print(f"  ⏳ Needs OCR (scanned document)")
            ocr_count += 1
        else:
            print(f"  ✓ Has text layer")
        
        ocr_pdf = _ensure_ocr(src_pdf)
        folder_path = os.path.dirname(os.path.relpath(src_pdf, data_dir))
        basket = _basket_from_path(folder_path)

        pdf_chunks = 0
        with fitz.open(ocr_pdf) as doc:
            print(f"  📄 Pages: {len(doc)} | Basket: {basket}")
            for page_idx in range(len(doc)):
                page_num = page_idx + 1
                text = doc[page_idx].get_text("text")
                if not text:
                    continue
                sents = _split_sentences(text)
                if not sents:
                    continue
                for i, chunk in enumerate(_chunk_sentences(sents)):
                    # Truncate oversized chunks
                    chunk = _truncate_chunk(chunk)
                    if len(chunk) < 50:  # Skip tiny chunks
                        skipped_chunks += 1
                        continue
                        
                    span_id = f"p{page_num}_c{i+1}"
                    meta = {
                        "pdf_name": os.path.basename(ocr_pdf),
                        "page": page_num,
                        "span_id": span_id,
                        "folder_path": folder_path,
                        "basket": basket,
                        "relpath": os.path.join(folder_path, os.path.basename(ocr_pdf)),
                    }
                    docs.append(Document(page_content=chunk, metadata=meta))
                    pdf_chunks += 1

        total_chunks += pdf_chunks
        print(f"  ✓ Chunks created: {pdf_chunks}")

        # Flush in smaller batches to avoid exceeding embedding context limits
        while len(docs) >= 50:
            batch = docs[:50]
            docs = docs[50:]
            print(f"  💾 Flushing batch of {len(batch)} chunks...")
            _add_documents_safely(vectordb, batch)

    # Final flush in batches
    while docs:
        batch = docs[:50]
        docs = docs[50:]
        print(f"\n💾 Flushing final batch of {len(batch)} chunks...")
        _add_documents_safely(vectordb, batch)

    # Auto-persisted by modern Chroma
    print("\n" + "="*70)
    print("INDEXING COMPLETE")
    print("="*70)
    print(f"Total PDFs processed: {total_pdfs}")
    print(f"PDFs requiring OCR: {ocr_count}")
    print(f"Total chunks created: {total_chunks}")
    print(f"Chunks skipped (too small): {skipped_chunks}")
    print(f"Vector store: {persist_dir}")
    print(f"Collection: {collection}")
    print("="*70)

if __name__ == "__main__":
    build_index()