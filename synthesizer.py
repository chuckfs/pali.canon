# synthesizer.py
from typing import List, Dict
from langchain_ollama import OllamaLLM
from config import LLM, MIN_HITS

# System prompt with grounding rules
SYS = """You are a wise and compassionate scholar of the Pāli Canon. Your goal is to not just answer questions, but to provide insightful, reflective, and thought-provoking responses based on the provided passages.

GUIDELINES:
- Freely quote from the text to illustrate your points.
- Connect concepts and ideas from different passages to offer a deeper understanding.
- Where appropriate, you can ask reflective questions to encourage the user to think more deeply.
- Always cite your sources at the end of your response in the format: 'folder/filename.pdf — p.<page>'.

CRITICAL RULES:
1. ONLY cite passages that appear in the Context section below.
2. If the Context does not contain information to answer the question, say: "The retrieved passages do not directly address this question."
3. NEVER invent or paraphrase quotes that don't appear verbatim in the Context.
4. If you are uncertain, prefix your answer with "Based on limited evidence..."
5. Do not make up teachings, suttas, or quotes that are not in the provided Context."""

def _format_context(hits: List[Dict]) -> str:
    lines = []
    for i, h in enumerate(hits, 1):
        # Use relpath if available, fall back to pdf_name
        path = h.get("relpath") or h.get("pdf_name")
        header = f"[{i}] {path} p.{h['page']}"
        body = h["text"].strip().replace("\n", " ")
        lines.append(f"{header}\n{body}")
    return "\n\n".join(lines)

def _format_sources(hits: List[Dict]) -> str:
    uniq = []
    seen = set()
    for h in hits:
        # Use relpath if available, fall back to pdf_name
        path = h.get("relpath") or h.get("pdf_name")
        sig = (path, h["page"])
        if sig not in seen:
            seen.add(sig)
            uniq.append(f"{path} — p.{h['page']}")
    return "Sources:\n" + "\n".join(f"- {s}" for s in uniq)

def synthesize(query: str, hits: List[Dict]) -> str:
    # Grounding safeguard: no hits at all
    if not hits:
        return ("I couldn't find relevant passages for this question in the indexed texts. "
                "Please try rephrasing your question, or check that the relevant texts are indexed.")
    
    # Grounding safeguard: too few hits for confident answer
    if len(hits) < MIN_HITS:
        sources = _format_sources(hits)
        return (f"I found only {len(hits)} potentially relevant passage(s), which may not be "
                f"sufficient for a complete answer. Here are the sources I found:\n\n{sources}\n\n"
                "Try rephrasing your question or using more specific terms from the Canon.")
    
    llm = OllamaLLM(model=LLM)
    ctx = _format_context(hits)
    prompt = f"{SYS}\n\nQuestion: {query}\n\nContext:\n{ctx}\n\nAnswer:"
    answer = llm.invoke(prompt)
    return f"{answer}\n\n{_format_sources(hits)}"

# Workbook entry generator with same grounding safeguards
def synthesize_workbook_entry(topic: str, hits: List[Dict]) -> str:
    """
    Generates a workbook entry with a specific format for beginners.
    """
    # Grounding safeguard
    if not hits:
        return "## No Passages Found\n\nCould not find relevant passages for this topic."
    
    if len(hits) < MIN_HITS:
        sources = _format_sources(hits)
        return (f"## Limited Sources\n\nOnly {len(hits)} passage(s) found, which may not be "
                f"sufficient for a complete workbook entry.\n\n{sources}")
    
    WORKBOOK_SYS = f"""You are a gentle and encouraging guide to the Pāli Canon, creating a daily workbook for a beginner. The topic for today is: "{topic}".

Based on the provided passages, please generate a workbook entry with the following sections, clearly separated by Markdown headings:

### Daily Passage
**Quote one key passage verbatim** from the provided context that best introduces today's topic. Please use Markdown blockquote formatting for the quote. Immediately after the quote, provide a modern, easy-to-understand translation.

### Extended Reading
Cite 2-3 other relevant passages from the context. Do not quote them, but provide the **full file path and page number** for further study (e.g., "sutta_pitaka/samyutta_nikaya1.pdf — p.112").

### The Day's Teaching
In a few simple sentences, explain the core teaching of the daily passage. What is the main takeaway for a beginner today?

### Journal Prompt
Provide one open-ended journal prompt that encourages the reader to reflect on today's teaching and how it might apply to their own life.

CRITICAL: Only use passages from the provided Context. Do not invent quotes or teachings."""

    llm = OllamaLLM(model=LLM)
    ctx = _format_context(hits)
    prompt = f"{WORKBOOK_SYS}\n\nContext:\n{ctx}\n\nWorkbook Entry:"
    
    workbook_entry = llm.invoke(prompt)
    
    return f"{workbook_entry}\n\n{_format_sources(hits)}"