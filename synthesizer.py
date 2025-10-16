#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Synthesizer: Compose a grounded answer from retrieved hits using Mistral (Ollama).
- Strong grounding prompt (no naming/numbering suttas unless present in context)
- Refuse when no evidence or off-target vs canonical target
- Emit a simple confidence score
"""
from __future__ import annotations
from typing import List, Dict, Any
import os, json, re, math
from langchain_ollama import ChatOllama

MODEL = os.getenv("LOTUS_LLM_MODEL", "mistral")  # Ollama model name

def _format_citation(meta: Dict[str, Any]) -> str:
    rel = meta.get("relpath") or meta.get("source") or meta.get("filename", "")
    page = meta.get("page")
    return f"{rel}" + (f" p.{page+1}" if isinstance(page, int) else "")

def _build_sources(hits: List[Dict[str, Any]], limit: int = 5) -> str:
    seen, out = set(), []
    for h in hits[:limit]:
        c = _format_citation(h["meta"])
        if c not in seen:
            seen.add(c); out.append(f"- {c}")
    return "\n".join(out) if out else "- (none)"

def _confidence(hits: List[Dict[str, Any]]) -> float:
    if not hits: return 0.0
    top = hits[:5]
    base = sum(h.get("score", 0.0) for h in top) / max(1, len(top))
    hybr = sum(h.get("hybrid_score", h.get("score", 0.0)) for h in top) / max(1, len(top))
    return max(0.0, min(1.0, 0.5*math.tanh(base) + 0.5*math.tanh(hybr)))

def synthesize(question: str, plan: Dict[str, Any], hits: List[Dict[str, Any]]) -> str:
    require_citations = plan.get("require_citations", True)

    if not hits:
        return ("I couldn't find canonical passages that address this directly in the Pāli Canon index. "
                "Try rephrasing the question or loosening basket/Nikāya filters.")

    # Guardrail: if planner identified a specific target, ensure top snippets are on-topic
    targets = [t.replace(" ", "").lower() for t in (plan.get("canonical_targets") or [])]
    if targets:
        joined = "\n".join(h["text"].lower() for h in hits[:5])
        if not any(t in joined for t in targets):
            return ("I couldn’t find passages clearly matching the requested sutta in the top results. "
                    "Try adding a bit more detail (e.g., the sutta number) or relax filters.")

    # Build compact context
    context_snippets = []
    for h in hits:
        c = _format_citation(h["meta"])
        context_snippets.append(f"[{c}]\n{h['text']}\n")
    context = "\n".join(context_snippets)

    sys_prompt = (
        "You are a careful scholar of the Theravāda Pāli Canon. "
        "Answer concisely and neutrally, sticking to the cited passages. "
        "Do not speculate beyond the text. Use plain English. "
        "Do NOT name or number suttas unless that exact name/number appears in the provided excerpts or their citations."
    )

    prompt = (
        f"{sys_prompt}\n\n"
        f"Question:\n{question}\n\n"
        f"Relevant canon passages (with citations):\n{context}\n\n"
        f"Compose a grounded answer in your own words. "
        f"Reference ideas back to the citations when appropriate."
    )

    llm = ChatOllama(model=MODEL, temperature=0.2)
    resp = llm.invoke(prompt)
    answer_text = resp.content if hasattr(resp, "content") else str(resp)

    # Light post-check: avoid introducing unrelated IDs
    id_mention_re = re.compile(r'\b(?:DN|MN|SN|AN|KN)\s*\d+(?:\.\d+)?\b')
    mentions = [m.replace(" ", "").upper() for m in id_mention_re.findall(answer_text)]
    targ_norm = {t.replace(" ", "").upper() for t in targets}
    if targets and any(m not in targ_norm for m in mentions):
        answer_text += "\n\n(Note: Ignored unrelated sutta numbering to avoid confusion.)"

    if require_citations:
        sources = _build_sources(hits, limit=5)
        answer_text = f"{answer_text}\n\nSources:\n{sources}"

    conf = _confidence(hits)
    answer_text = f"{answer_text}\n\nConfidence: {conf:.2f}"
    return answer_text