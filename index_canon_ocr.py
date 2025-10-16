# index_canon_ocr.py
import os, sys, subprocess, shutil, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

# --------- ENV / PATHS ---------
HOME = Path.home()
ROOT = Path(os.getenv("PALI_PROJECT_ROOT", HOME / "PaLi-CANON"))
DATA = ROOT / "data" / "pali_canon"            # your cleaned corpus
OCR_CACHE = ROOT / "ocr_cache"                  # OCR mirror cache
CHROMA_DIR = Path(os.getenv("LOTUS_CHROMA_DIR", ROOT / "chroma"))
COLLECTION = os.getenv("LOTUS_CHROMA_COLLECTION", "lotus_canon")
EMBED_MODEL = os.getenv("LOTUS_EMBED_MODEL", "nomic-embed-text")

# Tesseract languages (romanized Pali: 'eng' is fine; add more if you have Devanagari, etc.)
OCR_LANGS = os.getenv("OCR_LANGS", "eng")

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

# --------- UTILS ---------
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
    # mirror the directory structure under OCR_CACHE
    rel = rel_to_data(src_pdf)
    return (OCR_CACHE / rel).with_suffix(".pdf")

def ensure_dir(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)

def need_ocr(src: Path, dst: Path) -> bool:
    if not dst.exists():
        return True
    # re-OCR if source is newer than cached output
    return src.stat().st_mtime > dst.stat().st_mtime

def run_ocr(src: Path, dst: Path) -> None:
    """Always force OCR to get a clean text layer."""
    ensure_dir(dst)
    # ocrmypdf args tuned for speed & robustness:
    # --force-ocr : ignore existing text, do OCR always
    # --skip-big : skip absurd pages (safety), remove if you prefer 100% coverage
    # --jobs N : parallelize within file
    # --optimize 0 : skip heavy image recompression to speed up
    cmd = [
        "ocrmypdf",
        "--force-ocr",
        "--optimize", "0",
        "--jobs", str(max(1, os.cpu_count() or 2)),
        "--language", OCR_LANGS,
        str(src),
        str(dst),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        # If OCR fails for some PDF, surface a concise message and move on
        print(f"[OCR FAIL] {src} -> {dst}\n{e.stderr.decode(errors='ignore')[:500]}", file=sys.stderr)
        # As a fallback, try to just copy to cache so we don't block indexing entirely
        shutil.copy2(src, dst)

# --------- OCR ALL PDFs (with caching & progress) ---------
def ocr_all_pdfs(pdfs: List[Path], max_workers: int = max(2, (os.cpu_count() or 4) // 2)) -> List[Path]:
    """Return list of OCRed PDF paths in the same order."""
    to_process = []
    results = [None] * len(pdfs)

    for i, src in enumerate(pdfs):
        dst = ocr_target_for(src)
        if need_ocr(src, dst):
            to_process.append((i, src, dst))
        else:
            results[i] = dst

    total = len(pdfs)
    todo = len(to_process)
    done = total - todo
    print(f"OCR cache directory: {OCR_CACHE}")
    print(f"PDFs total: {total} | need OCR: {todo} | cached OK: {done}")

    if to_process:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futs = {
                ex.submit(run_ocr, src, dst): (i, src, dst)
                for (i, src, dst) in to_process
            }
            completed = 0
            last_log = time.time()
            for fut in as_completed(futs):
                i, src, dst = futs[fut]
                try:
                    fut.result()
                    results[i] = dst
                except Exception as e:
                    print(f"[OCR ERROR] {src}: {e}", file=sys.stderr)
                    # fallback: use original if OCR failed hard
                    results[i] = src
                completed += 1
                # light progress every ~1s
                if time.time() - last_log > 1:
                    print(f"… OCR {completed}/{todo}", end="\r")
                    last_log = time.time()

        print(f"OCR complete: {todo}/{todo}")

    # Safety: any None means fall back to original
    for i, r in enumerate(results):
        if r is None:
            results[i] = ocr_target_for(pdfs[i]) if ocr_target_for(pdfs[i]).exists() else pdfs[i]

    return results

# --------- INDEX ---------
def main():
    # 1) collect PDFs
    pdfs = list(list_pdfs())
    if not pdfs:
        print(f"No PDFs found under {DATA}")
        return

    # 2) OCR pass (pure OCR, always)
    ocred_paths = ocr_all_pdfs(pdfs)

    # 3) split + embed
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1400,
        chunk_overlap=180,
        separators=["\n\n", "\n", ". ", " "],
    )
    emb = OllamaEmbeddings(model=EMBED_MODEL)

    # 4) Load OCR’d PDFs with PyPDFLoader
    raw_docs = []
    for src_pdf, ocr_pdf in zip(pdfs, ocred_paths):
        loader = PyPDFLoader(str(ocr_pdf))
        basket, nikaya = tags_from_path(src_pdf)
        for d in loader.load():
            # Keep source path metadata pointing to the ORIGINAL canonical path,
            # but note that the text came from OCR cache file.
            d.metadata.update({
                "basket": basket,
                "nikaya": nikaya,
                "filename": src_pdf.name,
                "relpath": str(src_pdf.relative_to(ROOT)),
                "tier": "canon",
                "source_kind": "ocr",               # for transparency
                "ocr_file": str(ocr_pdf.relative_to(ROOT)),  # where text actually came from
            })
            raw_docs.append(d)

    splits = splitter.split_documents(raw_docs)

    db = Chroma(
        collection_name=COLLECTION,
        persist_directory=str(CHROMA_DIR),
        embedding_function=emb,
    )
    db.add_documents(splits)
    print(f"Indexed {len(splits)} chunks from {len(raw_docs)} PDFs into {CHROMA_DIR} [{COLLECTION}].")

if __name__ == "__main__":
    main()
