# synthesizer.py
from typing import List, Dict
from langchain_ollama import OllamaLLM
from config import LLM

# This is the new, more conversational system prompt
SYS = """You are a wise and compassionate scholar of the Pāli Canon. Your goal is to not just answer questions, but to provide insightful, reflective, and thought-provoking responses based on the provided passages.
- Freely quote from the text to illustrate your points.
- Connect concepts and ideas from different passages to offer a deeper understanding.
- Where appropriate, you can ask reflective questions to encourage the user to think more deeply.
- Always cite your sources at the end of your response in the format: 'filename.pdf — p.<page>'.
- If the passages don't contain a clear answer, you can say so, but you can also offer some general wisdom from the Canon that might be related to the user's query."""

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

# This is the new function for generating workbook entries
def synthesize_workbook_entry(topic: str, hits: List[Dict]) -> str:
    """
    Generates a workbook entry with a specific format for beginners.
    """
    WORKBOOK_SYS = f"""You are a gentle and encouraging guide to the Pāli Canon, creating a daily workbook for a beginner. The topic for today is: "{topic}".

Based on the provided passages, please generate a workbook entry with the following sections, clearly separated by Markdown headings:

### Daily Passage
Select one key passage from the provided context that best introduces the topic. Provide a modern, easy-to-understand translation of this passage.

### Extended Reading
Cite 2-3 other relevant passages from the context. Do not quote them, but provide the file name and page number for further study (e.g., "samyutta_nikaya1.pdf — p.112").

### The Day's Teaching
In a few simple sentences, explain the core teaching of the daily passage. What is the main takeaway for a beginner?

### Journal Prompt
Provide one open-ended journal prompt that encourages the reader to reflect on the day's teaching and how it might apply to their own life.
"""

    llm = OllamaLLM(model=LLM)
    ctx = _format_context(hits)
    prompt = f"{WORKBOOK_SYS}\n\nContext:\n{ctx}\n\nWorkbook Entry:"
    
    workbook_entry = llm.invoke(prompt)
    
    return f"{workbook_entry}\n\n{_format_sources(hits)}"
