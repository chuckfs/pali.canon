# index_canon.py
import os, sys, time, shutil, subprocess
from pathlib import Path
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

# ----------------- ENV / PATHS -----------------
HOME = Path.home()
ROOT = Path(os.getenv("PALI_PROJECT_ROOT", HOME / "PaLi-CANON"))
DATA = ROOT / "data" / "pali_canon"          # your cleaned corpus
OCR_CACHE = ROOT / "ocr_cache"               # OCR output mirror
CHROMA_DIR = Path(os.getenv("LOTUS_CHROMA_DIR", ROOT / "chroma"))
COLLECTION = os.getenv("LOTUS_CHROMA_COLLECTION", "lotus_canon")
EMBED_MODEL = os.getenv("LOTUS_EMBED_MODEL", "nomic-embed-text")
OCR_LANGS = os.getenv("OCR_LANGS", "eng")    # add +san if you have Devanagari: "eng+san"
UPSERT_BATCH = int(os.getenv("CHROMA_BATCH", "1000"))

# expected subfolders inside data/pali_canon
CANON_DIRS = [
    "vinaya_pitaka",
    "sutta_pitaka/digha_nikaya",
    "sutta_pitaka/majjhima_nikaya",
    "sutta_pitaka/samyutta_nikaya",
    "sutta_pitaka/anguttara_nikaya",
    "sutta_pitaka/khuddaka_nikaya",
    "abhidhamma_pitaka",
]

# ----------------- HELPERS -----------------
def list_pdfs() -> List[Path]:
    for sub in CANON_DIRS:
        base = DATA / sub
        if base.exists():
            yield from base.rglob("*.pdf")

def rel_to_data(p: Path) -> Path:
    return p.relative_to(DATA)

def tags_from_path(pdf_path: Path) -> Tuple[str, str]:
    parts = pdf_path.relative_to(DATA).parts
    basket = parts[0] if len(parts) > 0 else ""
    nikaya = parts[1] if len(parts) > 1 else ""
    return basket, nikaya

def ocr_target_for(src_pdf: Path) -> Path:
    rel = rel_to_data(src_pdf)
    return (OCR_CACHE / rel).with_suffix(".pdf")

def ensure_parent(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)

def need_ocr(src: Path, dst: Path) -> bool:
    if not dst.exists():
        return True
    return src.stat().st_mtime > dst.stat().st_mtime

def run_ocr(src: Path, dst: Path):
    """Force OCR on every file to get a clean text layer. Falls back to copy on failure."""
    ensure_parent(dst)
    cmd = [
        "ocrmypdf",
        "--force-ocr",
        "--optimize", "0",
        "--jobs", str(max(1, (os.cpu_count() or 2))),
        "--language", OCR_LANGS,
        str(src),
        str(dst),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        # Log concise error and fall back
        msg = e.stderr.decode(errors="ignore")
        print(f"[OCR FAIL] {src} -> {dst}\n{msg[:500]}", file=sys.stderr)
        shutil.copy2(src, dst)

def ocr_all(pdfs: List[Path], max_workers: int = max(2, (os.cpu_count() or 4) // 2)) -> List[Path]:
    """Pure OCR for all PDFs with caching + progress. Returns list of OCR'd paths aligned to input."""
    results: List[Path] = [None] * len(pdfs)  # type: ignore
    to_process = []

    for i, src in enumerate(pdfs):
        dst = ocr_target_for(src)
        if need_ocr(src, dst):
            to_process.append((i, src, dst))
        else:
            results[i] = dst

    total = len(pdfs)
    todo = len(to_process)
    print(f"OCR cache: {OCR_CACHE}")
    print(f"PDFs total: {total} | need OCR: {todo} | cached OK: {total - todo}")

    if to_process:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futs = {ex.submit(run_ocr, src, dst): (i, src, dst) for (i, src, dst) in to_process}
            done = 0
            last = time.time()
            for fut in as_completed(futs):
                i, src, dst = futs[fut]
                try:
                    fut.result()
                    results[i] = dst
                except Exception as e:
                    print(f"[OCR ERROR] {src}: {e}", file=sys.stderr)
                    results[i] = dst if dst.exists() else src
                done += 1
                if time.time() - last > 1:
                    print(f"… OCR {done}/{todo}", end="\r")
                    last = time.time()
        print(f"OCR complete: {todo}/{todo}")

    # any None -> fallback to source or existing dst
    for i, r in enumerate(results):
        if r is None:
            dst = ocr_target_for(pdfs[i])
            results[i] = dst if dst.exists() else pdfs[i]

    return results

def chunked(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]

# ----------------- MAIN -----------------
def main():
    pdfs = list(list_pdfs())
    if not pdfs:
        print(f"No PDFs found under {DATA}")
        return

    # 1) Pure OCR
    ocred = ocr_all(pdfs)

    # 2) Splitter + Embeddings
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1400, chunk_overlap=180, separators=["\n\n", "\n", ". ", " "]
    )
    emb = OllamaEmbeddings(model=EMBED_MODEL)

    # 3) Load OCR'd PDFs, keep metadata pointing to canonical source path
    raw_docs = []
    for src_pdf, ocr_pdf in zip(pdfs, ocred):
        loader = PyPDFLoader(str(ocr_pdf))
        basket, nikaya = tags_from_path(src_pdf)
        for d in loader.load():
            d.metadata.update({
                "basket": basket,
                "nikaya": nikaya,
                "filename": src_pdf.name,
                "relpath": str(src_pdf.relative_to(ROOT)),
                "tier": "canon",
                "source_kind": "ocr",
                "ocr_file": str(ocr_pdf.relative_to(ROOT)),
            })
            raw_docs.append(d)

    # 4) Split docs and filter empties
    splits = splitter.split_documents(raw_docs)
    splits = [s for s in splits if s.page_content and s.page_content.strip()]
    print(f"Prepared {len(splits)} non-empty chunks from {len(raw_docs)} PDF pages")

    # 5) Create / open Chroma and upsert in safe batches
    db = Chroma(
        collection_name=COLLECTION,
        persist_directory=str(CHROMA_DIR),
        embedding_function=emb,
    )

    total = len(splits)
    done = 0
    for i, batch in enumerate(chunked(splits, UPSERT_BATCH), start=1):
        db.add_documents(batch)
        done += len(batch)
        print(f"Upserted batch {i}: {done}/{total} chunks")

    print(f"Indexed {total} chunks into {CHROMA_DIR} [{COLLECTION}].")

if __name__ == "__main__":
    main()