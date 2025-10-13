# synthesizer.py — Stage 3: Generative synthesis (local Mistral via Ollama)
# - Writes the final answer using ONLY retrieved sources
# - Enforces inline citations based on provided metadata
# - Cleans labels (no absolute paths), prefers canonical refs

from __future__ import annotations
from typing import List, Dict, Any
from models_local import llm
import os

SYSTEM = """You are a careful Theravāda assistant.
Answer ONLY using the retrieved sources provided below. Do not invent citations.

Rules:
- Cite ONLY references present in the provided metadatas (ref/nikaya/number/source/page).
- If a canonical correction is needed (e.g., 'not DN 16; correct is SN 35.28'), you may say so,
  but do NOT fabricate a citation that isn't present in the sources.
- When discussing sense bases, use SIX (eye, ear, nose, tongue, body, mind).
- Inline citation format: [SN 35.28] or [cowelljataka2.pdf p.245] from the metadata.
- Keep a calm, clear tone. 5–10 sentences is ideal.
"""

def _label_from_meta(m: Dict[str, Any]) -> str:
    """Build a compact, clean citation label from metadata."""
    if not m:
        return ""
    ref    = m.get("ref")
    nikaya = m.get("nikaya") or m.get("Nikaya")
    number = m.get("number") or m.get("sutta_no")
    source = m.get("source") or m.get("file") or ""
    page   = m.get("page")

    # Prefer explicit canonical ref
    if ref:
        return str(ref)

    # Else Nikāya + number (e.g., "SN 35.28")
    if nikaya or number:
        return f"{nikaya or ''} {number or ''}".strip()

    # Else fallback to filename (+ page) without absolute paths
    if source:
        base = os.path.basename(str(source))
        if page not in (None, "", 0):
            return f"{base} p.{page}"
        return base

    return ""

def _fmt_sources(hits: List[Dict[str, Any]]) -> str:
    """Present sources in a way the model can cite safely."""
    blocks = []
    for h in hits or []:
        m = h.get("meta", {}) or {}
        label = _label_from_meta(m)
        header = f"--- [{label}]" if label else "--- (unlabeled source)"
        text = (h.get("text") or "").strip()
        blocks.append(f"{header}\n{text}\n")
    return "\n".join(blocks) if blocks else "NO_SOURCES"

def synthesize(question: str, plan: Dict[str, Any], hits: List[Dict[str, Any]]) -> str:
    packed = _fmt_sources(hits)
    prompt = f"""User question:
{question}

Planner output (for transparency):
{plan}

Retrieved sources (use ONLY these; do not cite anything else):
{packed}

Write a clear answer (5–10 sentences) with inline citations that match the labels above.
End with 2–3 “Suggested readings” chosen ONLY from the retrieved sources, using the same labels.
"""
    return llm(prompt, system=SYSTEM, temperature=0.2)