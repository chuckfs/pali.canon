# synthesizer.py
from typing import List, Dict
from langchain_ollama import OllamaLLM
from config import LLM

SYS = """You are a careful, neutral scholar. Answer ONLY using the provided passages.
- Include 1–2 short quotes when helpful.
- NEVER invent IDs or page numbers.
- End with a Sources list in the format: 'filename.pdf — p.<page>'.
"""

def _format_context(hits: List[Dict]) -> str:
    lines = []
    for i, h in enumerate(hits, 1):
        header = f"[{i}] {h['pdf_name']} p.{h['page']}"
        body = h["text"].strip().replace("\n", " ")
        lines.append(f"{header}\n{body}")
    return "\n\n".join(lines)

def _format_sources(hits: List[Dict]) -> str:
    uniq = []
    seen = set()
    for h in hits:
        sig = (h["pdf_name"], h["page"])
        if sig not in seen:
            seen.add(sig)
            uniq.append(f"{h['pdf_name']} — p.{h['page']}")
    return "Sources:\n" + "\n".join(f"- {s}" for s in uniq)

def synthesize(query: str, hits: List[Dict]) -> str:
    if not hits:
        return "I couldn’t find passages for that in your index. Try reindexing or broadening the query."
    llm = OllamaLLM(model=LLM)
    ctx = _format_context(hits)
    prompt = f"{SYS}\n\nQuestion: {query}\n\nContext:\n{ctx}\n\nAnswer:"
    answer = llm.invoke(prompt)
    return f"{answer}\n\n{_format_sources(hits)}"