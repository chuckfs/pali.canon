# web/app.py
import os, re, json, time, gradio as gr
from typing import List, Tuple
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_chroma import Chroma
from langchain.prompts import PromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain

# ----------------- ENV (repo-aware defaults) -----------------
HOME = os.path.expanduser("~")
PROJECT = os.path.expanduser(os.environ.get("PALI_PROJECT_ROOT", f"{HOME}/PaLi-CANON"))
PERSIST_DIR = os.path.expanduser(os.environ.get("LOTUS_CHROMA_DIR", f"{PROJECT}/chroma"))
COLLECTION  = os.environ.get("LOTUS_CHROMA_COLLECTION", "lotus_canon")
EMBED_MODEL = os.environ.get("LOTUS_EMBED_MODEL", "nomic-embed-text")
DEFAULT_LLM = os.environ.get("LOTUS_LLM_MODEL", "mistral")

# ----------------- Helpers -----------------
NIKAYA_FULL = {
    "DN":"Dīgha Nikāya","MN":"Majjhima Nikāya","SN":"Saṃyutta Nikāya",
    "AN":"Aṅguttara Nikāya","KN":"Khuddaka Nikāya"
}
ABBR_RX = re.compile(r'\b(DN|MN|SN|AN|KN)\s+(\d+(?:\.\d+)?)\b')
def expand_citations(t: str) -> str:
    return ABBR_RX.sub(lambda m: f"{NIKAYA_FULL.get(m.group(1), m.group(1))} ({m.group(1)} {m.group(2)})", t)

def build_db():
    emb = OllamaEmbeddings(model=EMBED_MODEL)
    return Chroma(embedding_function=emb, persist_directory=PERSIST_DIR, collection_name=COLLECTION)

def corpus_stats() -> str:
    try:
        db = build_db()
        # Chroma doesn't expose count directly; do an empty search to infer size
        # (cheap approximation)
        count = db._collection.count()
        return f"**Collection:** `{COLLECTION}`  \n**Embeddings:** `{EMBED_MODEL}`  \n**Docs indexed:** **{count:,}**"
    except Exception as e:
        return f"_Corpus unavailable_: {e}"

PROMPT = PromptTemplate.from_template(
    "You are a careful Theravāda teacher. Use ONLY the provided context from the user's local Pāli Canon corpus. "
    "Return headings, bullet points, brief *italic* quotes with FULL citations (e.g., Dīgha Nikāya (DN 22)), and a 'Suggested Readings' list.\n\n"
    "Question:\n{question}\n\nContext:\n{context}\n"
)

def retrieve(db, question: str, k=18, fetch_k=80, lam=0.75):
    retr = db.as_retriever(search_type="mmr", search_kwargs={"k":k, "fetch_k":fetch_k, "lambda_mult":lam})
    docs = retr.invoke(question)
    if not docs:
        docs = db.as_retriever(search_type="similarity", search_kwargs={"k":k}).invoke(question)
    return docs

def format_sources(docs) -> List[dict]:
    cards, seen = [], set()
    for d in docs or []:
        m = d.metadata or {}
        key = (m.get("source", "?"), m.get("page", "?"))
        if key in seen: 
            continue
        seen.add(key)
        cards.append({
            "file": os.path.basename(m.get("source","?")),
            "page": m.get("page","?"),
            "collection": NIKAYA_FULL.get((m.get("collection") or m.get("nikaya") or ""), None)
        })
    return cards

def render_source_cards(cards: List[dict]) -> str:
    if not cards:
        return "_No sources (check index/env)_"
    lines = []
    for c in cards:
        tag = f"<span class='tag'>{c['collection']}</span>" if c.get("collection") else ""
        lines.append(f"<div class='card'><div class='card-title'>{c['file']}</div>"
                     f"<div class='card-meta'>Page {c['page']} {tag}</div></div>")
    return "<div class='cards'>" + "".join(lines) + "</div>"

# ----------------- Core answer fn -----------------
def ask_pali(history, message, k, fetch_k, lam, temperature, model_name):
    t0 = time.time()
    db = build_db()
    docs = retrieve(db, message, k=int(k), fetch_k=int(fetch_k), lam=float(lam))
    llm = OllamaLLM(model=model_name or DEFAULT_LLM, temperature=float(temperature))
    chain = create_stuff_documents_chain(llm, PROMPT)
    out = chain.invoke({"question": message, "context": docs})
    out = expand_citations(out)

    src_cards = render_source_cards(format_sources(docs))
    elapsed = f"<div class='latency'>⏱ {time.time()-t0:.2f}s</div>"

    answer_md = out + "\n\n---\n**Sources**\n" + src_cards + elapsed
    history = (history or []) + [[message, answer_md]]
    return history, ""

def export_last(history):
    if not history:
        return None
    last = history[-1][1]
    content = re.sub(r"<.*?>", "", last)  # strip simple HTML from source cards
    path = os.path.join(PROJECT, "output", "answer.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return gr.File.update(value=path, visible=True)

# ----------------- UI -----------------
CSS = """
:root { --accent:#6d28d9; }
#wrap { max-width: 1100px; margin: 0 auto; }
.brand { display:flex; align-items:center; gap:.75rem; }
.brand img { width:34px; height:34px; border-radius:10px; }
.hero { display:flex; justify-content:space-between; align-items:center; }
.badge { font-size:.85rem; padding:.25rem .5rem; border:1px solid #9993; border-radius:8px; }
.sidebar .gr-group { border:1px solid #9993; border-radius:12px; padding:10px; }
.cards { display:grid; grid-template-columns: repeat(auto-fill, minmax(220px,1fr)); gap:10px; margin-top:.5rem;}
.card { border:1px solid #e5e7eb; border-radius:12px; padding:.6rem .7rem; background: var(--panel-background-fill); }
.card-title { font-weight:600; font-size:.95rem; }
.card-meta { font-size:.85rem; opacity:.75; margin-top:.2rem; }
.tag { display:inline-block; margin-left:.35rem; padding:.05rem .35rem; font-size:.75rem; border-radius:6px; background:#eef; color:#334; }
.latency { font-size:.8rem; opacity:.65; margin-top:.25rem; }
"""

PRESETS = [
    "Give a 1-page beginner lesson on Satipaṭṭhāna with a *Key passage* (≤120 words) and FULL Canon citations.",
    "Outline the Noble Eightfold Path with short practice prompts and citations (DN/MN/SN/AN/KN only).",
    "Design Month 1 of a 12-month curriculum (theme, summary ≤80 words, core canon readings, reflection).",
    "Explain Dependent Origination (paṭiccasamuppāda) with 3 key suttas and brief quotes."
]

with gr.Blocks(theme=gr.themes.Soft(primary_hue="purple", neutral_hue="slate"), css=CSS, title="PaLi-CANON") as demo:
    with gr.Column(elem_id="wrap"):
        with gr.Row(equal_height=True):
            with gr.Column(scale=5):
                gr.Markdown(
                    f"<div class='hero'><div class='brand'>"
                    f"<img src='https://em-content.zobj.net/source/apple/391/lotus_1faba.png'/>"
                    f"<div><h1>PaLi-CANON</h1><div class='badge'>Model: {DEFAULT_LLM} · Embeddings: {EMBED_MODEL}</div></div>"
                    f"</div></div>"
                )
            with gr.Column(scale=3, min_width=280, elem_classes="sidebar"):
                gr.Markdown("### Corpus")
                stats = gr.Markdown(corpus_stats())
                gr.Markdown("### Presets")
                preset = gr.Radio(PRESETS, value=PRESETS[0], label="", interactive=True)
        with gr.Row():
            with gr.Column(scale=5):
                chat = gr.Chatbot(height=520, show_copy_button=True, likeable=False, layout="bubble")
                with gr.Row():
                    msg = gr.Textbox(placeholder="Ask anything grounded in your local Canon…", label="")
                    btn = gr.Button("Ask", variant="primary")
                with gr.Accordion("Settings", open=False):
                    with gr.Row():
                        k = gr.Slider(8, 36, value=18, step=1, label="k (final hits)")
                        fetch_k = gr.Slider(20, 200, value=80, step=5, label="fetch_k (MMR pool)")
                        lam = gr.Slider(0.0, 1.0, value=0.75, step=0.05, label="MMR λ (diversity)")
                    with gr.Row():
                        temperature = gr.Slider(0.0, 1.2, value=0.4, step=0.1, label="Temperature")
                        model_name = gr.Textbox(value=DEFAULT_LLM, label="Ollama model", scale=2)
                with gr.Row():
                    export_btn = gr.Button("Export last answer → Markdown")
                    exported = gr.File(visible=False, label="Download")
            with gr.Column(scale=3, min_width=280):
                gr.Markdown("### Tips")
                gr.Markdown(
                    "- Prefer Canon anchors (DN/MN/SN/AN/KN) in your question.\n"
                    "- Ask for *Key passage* to include an italic excerpt.\n"
                    "- Use **Settings** to adjust retrieval diversity and model."
                )
                gr.Markdown("### Sources (from last answer)")
                sources_panel = gr.Markdown("_Ask something to see sources here._")

    # interactions
    def use_preset(p): return p
    preset.change(use_preset, preset, msg)
    btn.click(
        fn=ask_pali,
        inputs=[chat, msg, k, fetch_k, lam, temperature, model_name],
        outputs=[chat, msg]
    )
    msg.submit(
        fn=ask_pali,
        inputs=[chat, msg, k, fetch_k, lam, temperature, model_name],
        outputs=[chat, msg]
    )
    # update sources panel whenever chat changes (pull last)
    def last_sources(history):
        if not history: return "_No messages yet._"
        # naive parse: after '---\n**Sources**\n' we injected HTML cards
        last = history[-1][1]
        parts = last.split("**Sources**")
        if len(parts) < 2: return "_No sources in last answer._"
        html = parts[-1]
        return html
    chat.change(last_sources, chat, sources_panel)

    export_btn.click(export_last, chat, exported)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, favicon_path=None)
