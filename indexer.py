# indexer.py
import os
import re
import shutil
import subprocess
import unicodedata
from typing import List, Optional

import fitz  # PyMuPDF
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from config import DATA, CHROMA, COLL, EMBED, CHUNK_SIZE, CHUNK_OVERLAP

# OCR cache mirrors the data tree so we don't re-OCR on every run
OCR_CACHE = os.path.join(os.path.dirname(DATA), "ocr_cache")

# Sentence-ish splitter (lightweight; handles A/Pāli capitals too)
_SPLIT_RE = re.compile(r"(?<=[\.!?])\s+(?=[A-ZĀĪŪṄÑṬḌḶ])")

# Hard limit for chunk size (nomic-embed-text has 8192 token limit, ~4 chars per token)
MAX_CHUNK_CHARS = 6000

# === CITATION EXTRACTION PATTERNS ===

# Pattern for standard references: DN 1, MN 21, SN 35.28, AN 4.159, Dhp 21, Ud 1.10, It 112, etc.
# Supports: "SN 35.28", "SN35.28", "SN.35.28", "SN-35.28", "SN:35:28", "MN.21"
NIKAYA_REF_RE = re.compile(
    r"\b(DN|MN|SN|AN|Dhp|Ud|It|Sn|Thag|Thig|Khp|Vv|Pv|Ja)"
    r"\s*[-\.:]?\s*"
    r"(\d{1,3})"
    r"(?:\s*[-\.:]\s*(\d{1,3}))?"
    r"\b",
    re.IGNORECASE,
)

# Book-name references like: "Dhammapada 21", "Udāna 1.10", "Itivuttaka 112"
BOOK_REF_RE = re.compile(
    r"\b(Dhammapada|Dhp|Udāna|Udana|Ud|Itivuttaka|It)\b\s*"
    r"(\d{1,3})(?:[\.:]\s*(\d{1,3}))?\b",
    re.IGNORECASE,
)

# Pattern for full nikaya names: "Majjhima Nikāya 21", "Saṃyutta Nikaya 35.28", etc.
FULL_NIKAYA_RE = re.compile(
    r"\b(Dīgha|Digha|Majjhima|Saṃyutta|Samyutta|Aṅguttara|Anguttara)\s+"
    r"(?:Nikāya|Nikaya)\s*[-\.:]?\s*"
    r"(\d{1,3})(?:\s*[-\.:]\s*(\d{1,3}))?\b",
    re.IGNORECASE,
)

# Pattern for sutta names (common ones) — optional "Sutta" suffix so names alone can match
SUTTA_NAME_RE = re.compile(
    r"\b(Dhammacakkappavattana|Anattalakkhaṇa|Anattalakkhana|Ādittapariyāya|Adittapariyaya|"
    r"Satipaṭṭhāna|Satipatthana|Mahāsatipaṭṭhāna|Mahasatipatthana|"
    r"Kālāma|Kalama|Sigālovāda|Sigalovada|Mahāparinibbāna|Mahaparinibbana|"
    r"Kakacūpama|Kakacupama|Ānāpānasati|Anapanasati)"
    r"(?:\s*Sutta\b)?",
    re.IGNORECASE,
)

# Nikaya abbreviation normalization
# IMPORTANT: do NOT map "sn" to "Sn" (Sutta Nipāta). Default "sn" => SN (Saṃyutta Nikāya).
# Only map Sutta Nipāta when explicitly signaled by text like "suttanipata"/"snp" or when user types "Sn".
NIKAYA_ABBREV = {
    "dn": "DN",
    "digha": "DN",
    "dīgha": "DN",
    "mn": "MN",
    "majjhima": "MN",
    "sn": "SN",
    "samyutta": "SN",
    "saṃyutta": "SN",
    "an": "AN",
    "anguttara": "AN",
    "aṅguttara": "AN",
    "dhp": "Dhp",
    "dhammapada": "Dhp",
    "ud": "Ud",
    "udana": "Ud",
    "udāna": "Ud",
    "it": "It",
    "itivuttaka": "It",
    # Sutta Nipāta (explicit only)
    "snp": "Sn",
    "suttanipata": "Sn",
    "suttanipāta": "Sn",
    "thag": "Thag",
    "theragatha": "Thag",
    "theragāthā": "Thag",
    "thig": "Thig",
    "therigatha": "Thig",
    "therīgāthā": "Thig",
    "khp": "Khp",
    "khuddakapatha": "Khp",
    "khuddakapāṭha": "Khp",
    "vv": "Vv",
    "vimanavatthu": "Vv",
    "vimānavatthu": "Vv",
    "pv": "Pv",
    "petavatthu": "Pv",
    "ja": "Ja",
    "jataka": "Ja",
    "jātaka": "Ja",
}

# Sutta name to reference mapping
SUTTA_NAME_TO_REF = {
    "dhammacakkappavattana": "SN 56.11",
    "anattalakkhaṇa": "SN 22.59",
    "anattalakkhana": "SN 22.59",
    "ādittapariyāya": "SN 35.28",
    "adittapariyaya": "SN 35.28",
    "satipaṭṭhāna": "MN 10",
    "satipatthana": "MN 10",
    "mahāsatipaṭṭhāna": "DN 22",
    "mahasatipatthana": "DN 22",
    "kālāma": "AN 3.65",
    "kalama": "AN 3.65",
    "sigālovāda": "DN 31",
    "sigalovada": "DN 31",
    "mahāparinibbāna": "DN 16",
    "mahaparinibbana": "DN 16",
    "kakacūpama": "MN 21",
    "kakacupama": "MN 21",
    "ānāpānasati": "MN 118",
    "anapanasati": "MN 118",
}


def _strip_diacritics(s: str) -> str:
    """Best-effort diacritic stripping for matching Pāli terms across OCR variants."""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _normalize_nikaya_token(raw: str) -> str:
    """
    Normalize a nikaya token like 'sn', 'SN', 'Dhp', 'ud' into canonical form.

    Key rule:
    - 'sn' => 'SN' (Saṃyutta Nikāya)
    - 'Sn' (capital S + lowercase n) => 'Sn' (Sutta Nipāta) (explicit)
    """
    if not raw:
        return raw

    # Preserve explicit "Sn" as Sutta Nipāta if the user typed it that way.
    if raw == "Sn":
        return "Sn"

    key = raw.lower()

    # Default: sn => SN
    if key == "sn":
        return "SN"

    mapped = NIKAYA_ABBREV.get(key)
    if mapped:
        return mapped

    return raw.upper()


def _extract_citations(text: str) -> List[str]:
    """Extract canonical citations from text (normalized and de-duplicated)."""
    citations = set()

    if not text:
        return []

    # 1) Standard abbreviations (DN 1, MN 21, SN 35.28, etc.)
    for match in NIKAYA_REF_RE.finditer(text):
        raw_nikaya = match.group(1)  # preserves original case (important for Sn)
        num1 = match.group(2)
        num2 = match.group(3)

        nikaya = _normalize_nikaya_token(raw_nikaya)

        if num2:
            citations.add(f"{nikaya} {num1}.{num2}")
        else:
            citations.add(f"{nikaya} {num1}")

    # 1b) Book-name references (Dhammapada 21, Udāna 1.10, Itivuttaka 112)
    for match in BOOK_REF_RE.finditer(text):
        raw_book = match.group(1)
        num1 = match.group(2)
        num2 = match.group(3)

        nikaya = NIKAYA_ABBREV.get(raw_book.lower(), raw_book)

        if num2:
            citations.add(f"{nikaya} {num1}.{num2}")
        else:
            citations.add(f"{nikaya} {num1}")

    # 2) Full nikaya names (Majjhima Nikāya 21)
    for match in FULL_NIKAYA_RE.finditer(text):
        nikaya_name = match.group(1).lower()
        num1 = match.group(2)
        num2 = match.group(3)

        nikaya = NIKAYA_ABBREV.get(nikaya_name, nikaya_name.upper()[:2])

        if num2:
            citations.add(f"{nikaya} {num1}.{num2}")
        else:
            citations.add(f"{nikaya} {num1}")

    # 3) Sutta names (with or without the word "Sutta")
    for match in SUTTA_NAME_RE.finditer(text):
        sutta_name = match.group(1).lower()
        ref = SUTTA_NAME_TO_REF.get(sutta_name)
        if ref:
            citations.add(ref)

    # 4) Diacritic-insensitive substring matching for sutta names (handles OCR variance)
    t_norm = _strip_diacritics(text).lower()
    for name, ref in SUTTA_NAME_TO_REF.items():
        name_norm = _strip_diacritics(name).lower()
        if name_norm and name_norm in t_norm:
            citations.add(ref)

    return sorted(citations)


def _infer_nikaya_from_path(folder_path: str, pdf_name: str) -> Optional[str]:
    """Infer nikaya from file path."""
    combined = (folder_path + "/" + pdf_name).lower()

    if "digha" in combined or "dialogues" in combined:
        return "DN"
    elif "majjhima" in combined:
        return "MN"
    elif "samyutta" in combined:
        return "SN"
    elif "anguttara" in combined:
        return "AN"
    elif "dhammapada" in combined:
        return "Dhp"
    elif "udana" in combined:
        return "Ud"
    elif "itivuttaka" in combined:
        return "It"
    elif "suttanipata" in combined:
        return "Sn"
    elif "theragatha" in combined:
        return "Thag"
    elif "therigatha" in combined:
        return "Thig"
    elif "khuddakapatha" in combined:
        return "Khp"
    elif "vimanavatthu" in combined:
        return "Vv"
    elif "petavatthu" in combined:
        return "Pv"
    elif "jataka" in combined:
        return "Ja"

    return None


def _has_text(pdf_path: str, pages: int = 3) -> bool:
    """
    Quick heuristic: check the first N pages for extractable text.
    If there's meaningful text, we can skip OCR and just copy into cache.
    """
    try:
        with fitz.open(pdf_path) as doc:
            n = min(len(doc), max(1, pages))
            for i in range(n):
                txt = doc[i].get_text("text") or ""
                if len(txt.strip()) >= 200:
                    return True
        return False
    except Exception:
        return False


def _ensure_ocr(pdf_path: str) -> str:
    """
    Ensure PDFs are OCR'd for consistent text extraction.

    - Cache is mirrored in OCR_CACHE
    - If the PDF already has text, we copy it into cache (fast path)
    - Otherwise, we OCR it once and cache the result
    """
    os.makedirs(OCR_CACHE, exist_ok=True)
    rel = os.path.relpath(pdf_path, DATA)
    out_pdf = os.path.join(OCR_CACHE, rel)
    os.makedirs(os.path.dirname(out_pdf), exist_ok=True)

    if os.path.exists(out_pdf):
        return out_pdf

    # Fast path: detectable text -> copy into cache
    if _has_text(pdf_path, pages=3):
        print("    ✓ Text detected, copying (no OCR needed)...")
        shutil.copy(pdf_path, out_pdf)
        return out_pdf

    print("    🔍 Running OCR...")
    tmp = out_pdf + ".tmp.pdf"
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


def _chunk_sentences(sents: List[str], max_len=CHUNK_SIZE, overlap=CHUNK_OVERLAP) -> List[str]:
    chunks, buf = [], []
    cur_len = 0
    for s in sents:
        if cur_len + len(s) + 1 > max_len and buf:
            chunks.append(" ".join(buf).strip())
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
    return text[:max_chars].rsplit(" ", 1)[0]


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
            print("    ⚠️ Batch failed, adding one-by-one...")
            for doc in docs:
                try:
                    vectordb.add_documents([doc])
                except Exception:
                    print(f"    ❌ Skipped chunk (too long): {len(doc.page_content)} chars")
        else:
            raise e


def build_index(data_dir=DATA, persist_dir=CHROMA, collection=COLL):
    os.makedirs(persist_dir, exist_ok=True)

    pdf_list = list(_iter_pdfs(data_dir))
    total_pdfs = len(pdf_list)

    if total_pdfs == 0:
        print(f"ERROR: No PDFs found in {data_dir}")
        return

    print("=" * 70)
    print("INDEXING PALI CANON")
    print("=" * 70)
    print(f"Source directory: {data_dir}")
    print(f"Vector store: {persist_dir}")
    print(f"PDFs found: {total_pdfs}")
    print(f"Chunk size: {CHUNK_SIZE} chars, overlap: {CHUNK_OVERLAP} chars")
    print("=" * 70)

    embeddings = OllamaEmbeddings(model=EMBED)
    vectordb = Chroma(
        collection_name=collection,
        embedding_function=embeddings,
        persist_directory=persist_dir,
    )

    docs: List[Document] = []
    total_chunks = 0
    skipped_chunks = 0
    chunks_with_citations = 0

    for pdf_idx, src_pdf in enumerate(pdf_list, 1):
        pdf_name = os.path.basename(src_pdf)
        print(f"\n[{pdf_idx}/{total_pdfs}] {pdf_name}")

        ocr_pdf = _ensure_ocr(src_pdf)
        folder_path = os.path.dirname(os.path.relpath(src_pdf, data_dir))
        basket = _basket_from_path(folder_path)
        nikaya = _infer_nikaya_from_path(folder_path, pdf_name)

        pdf_chunks = 0
        pdf_citations = 0

        with fitz.open(ocr_pdf) as doc:
            print(f"  📄 Pages: {len(doc)} | Basket: {basket} | Nikaya: {nikaya or 'unknown'}")
            for page_idx in range(len(doc)):
                page_num = page_idx + 1
                text = doc[page_idx].get_text("text")
                if not text:
                    continue

                sents = _split_sentences(text)
                if not sents:
                    continue

                for i, chunk in enumerate(_chunk_sentences(sents)):
                    chunk = _truncate_chunk(chunk)
                    if len(chunk) < 50:
                        skipped_chunks += 1
                        continue

                    citations = _extract_citations(chunk)
                    if citations:
                        pdf_citations += len(citations)
                        chunks_with_citations += 1

                    span_id = f"p{page_num}_c{i+1}"
                    meta = {
                        "pdf_name": os.path.basename(ocr_pdf),
                        "page": page_num,
                        "span_id": span_id,
                        "folder_path": folder_path,
                        "basket": basket,
                        "relpath": os.path.join(folder_path, os.path.basename(ocr_pdf)),
                        "nikaya": nikaya or "",
                        "citations": ",".join(citations) if citations else "",
                    }
                    docs.append(Document(page_content=chunk, metadata=meta))
                    pdf_chunks += 1

        total_chunks += pdf_chunks
        print(f"  ✓ Chunks: {pdf_chunks} | Citations found: {pdf_citations}")

        while len(docs) >= 50:
            batch = docs[:50]
            docs = docs[50:]
            print(f"  💾 Flushing batch of {len(batch)} chunks...")
            _add_documents_safely(vectordb, batch)

    while docs:
        batch = docs[:50]
        docs = docs[50:]
        print(f"\n💾 Flushing final batch of {len(batch)} chunks...")
        _add_documents_safely(vectordb, batch)

    print("\n" + "=" * 70)
    print("INDEXING COMPLETE")
    print("=" * 70)
    print(f"Total PDFs processed: {total_pdfs}")
    print(f"Total chunks created: {total_chunks}")
    print(f"Chunks with citations: {chunks_with_citations}")
    print(f"Chunks skipped (too small): {skipped_chunks}")
    print(f"Vector store: {persist_dir}")
    print(f"Collection: {collection}")
    print("=" * 70)


if __name__ == "__main__":
    build_index()
