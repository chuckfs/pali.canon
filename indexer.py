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

from config import DATA, CHROMA, COLL, EMBED

# ---- Chunking settings ----
SENT_LEN = 800
SENT_OVERLAP = 120

# OCR cache mirrors the data tree so we don't re-OCR on every run
OCR_CACHE = os.path.join(os.path.dirname(DATA), "ocr_cache")

# Sentence-ish splitter (lightweight; handles A/Pāli capitals too)
_SPLIT_RE = re.compile(r"(?<=[\.!?])\s+(?=[A-ZĀĪŪṄÑṬḌḶ])")

def _has_text(pdf_path: str) -> bool:
    """Quickly check if at least one of the first pages has a text layer."""
    try:
        with fitz.open(pdf_path) as doc:
            for p in range(min(3, len(doc))):
                if doc[p].get_text("text").strip():
                    return True
        return False
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
    tmp = out_pdf + ".tmp.pdf"
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    cmd = ["ocrmypdf", "--quiet", "--force-ocr", "--output-type", "pdf", pdf_path, tmp]
    subprocess.run(cmd, check=True)
    shutil.move(tmp, out_pdf)
    return out_pdf

def _iter_pdfs(root: str):
    for dirpath, _, files in os.walk(root):
        for f in files:
            if f.lower().endswith(".pdf"):
                yield os.path.join(dirpath, f)

def _split_sentences(text: str) -> List[str]:
    parts = _SPLIT_RE.split(text.strip())
    return [p.strip() for p in parts if p.strip()]

def _chunk_sentences(sents: List[str], max_len=SENT_LEN, overlap=SENT_OVERLAP) -> List[str]:
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

def _basket_from_path(path: str) -> str:
    low = path.lower()
    if "/vinaya" in low:
        return "vinaya"
    if "/abhidhamma" in low or "/abhi" in low:
        return "abhidhamma"
    return "sutta"

def build_index(data_dir=DATA, persist_dir=CHROMA, collection=COLL):
    os.makedirs(persist_dir, exist_ok=True)

    embeddings = OllamaEmbeddings(model=EMBED)
    vectordb = Chroma(
        collection_name=collection,
        embedding_function=embeddings,
        persist_directory=persist_dir,
    )

    docs: List[Document] = []
    for src_pdf in _iter_pdfs(data_dir):
        ocr_pdf = _ensure_ocr(src_pdf)
        pdf_name = os.path.basename(ocr_pdf)
        folder_path = os.path.dirname(os.path.relpath(src_pdf, data_dir))
        basket = _basket_from_path(folder_path)

        with fitz.open(ocr_pdf) as doc:
            for page_idx in range(len(doc)):
                page_num = page_idx + 1
                text = doc[page_idx].get_text("text")
                if not text:
                    continue
                sents = _split_sentences(text)
                if not sents:
                    continue
                for i, chunk in enumerate(_chunk_sentences(sents)):
                    span_id = f"p{page_num}_c{i+1}"
                    meta = {
                        "pdf_name": pdf_name,
                        "page": page_num,
                        "span_id": span_id,
                        "folder_path": folder_path,
                        "basket": basket,
                        "relpath": os.path.join(folder_path, pdf_name),
                    }
                    docs.append(Document(page_content=chunk, metadata=meta))

        # Flush per file to avoid giant batches
        if len(docs) >= 500:
            vectordb.add_documents(docs)
            docs = []

    if docs:
        vectordb.add_documents(docs)

    # Auto-persisted by modern Chroma
    print(f"Indexed into {persist_dir} / collection={collection} (auto-persist)")

if __name__ == "__main__":
    build_index()