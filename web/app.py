# web/app.py
import os, re
import gradio as gr
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_chroma import Chroma
from langchain.prompts import PromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain

# ---- env defaults (matches your CLI) ----
HOME = os.path.expanduser("~")
PERSIST_DIR = os.path.expanduser(os.environ.get("LOTUS_CHROMA_DIR", f"{HOME}/PaLi-CANON/chroma"))
COLLECTION  = os.environ.get("LOTUS_CHROMA_COLLECTION", "lotus_canon")
EMBED_MODEL = os.environ.get("LOTUS_EMBED_MODEL", "nomic-embed-text")

NIKAYA_FULL = {
    "DN":"Dīgha Nikāya","MN":"Majjhima Nikāya","SN":"Saṃyutta Nikāya",
    "AN":"Aṅguttara Nikāya","KN":"Khuddaka Nikāya"
}
ABBR_RX = re.compile(r'\b(DN|MN|SN|AN|KN)\s+(\d+(?:\.\d+)?)\b')
def expand_citations(text:str)->str:
    return ABBR_RX.sub(lambda m: f"{NIKAYA_FULL.get(m.group(1))} ({m.group(1)} {m.group(2)})", text)

PROMPT = PromptTemplate.from_template(
    "You are a careful Theravāda teacher. Use ONLY the provided context from the user's local Pāli Canon corpus. "
    "Do not invent citations. Synthesize lessons across multiple suttas.\n\n"
    "Question:\n{question}\n\nContext:\n{context}\n\n"
    "Return with headings, bullets, *brief italic quotes* with FULL citations, and a 'Suggested Readings' list.\n"
)

def build_db():
    emb = OllamaEmbeddings(model=EMBED_MODEL)
    return Chroma(embedding_function=emb, persist_directory=PERSIST_DIR, collection_name=COLLECTION)

def retrieve(db, question:str):
    retr = db.as_retriever(search_type="mmr", search_kwargs={"k":18, "fetch_k":80, "lambda_mult":0.75})
    docs = retr.invoke(question)
    if not docs:
        docs = db.as_retriever(search_type="similarity", search_kwargs={"k":25}).invoke(question)
    return docs

def answer(question):
    try:
        db   = build_db()
        docs = retrieve(db, question)
        llm  = OllamaLLM(model="mistral")
        chain = create_stuff_documents_chain(llm, PROMPT)
        out = chain.invoke({"question": question, "context": docs})
        # Sources block
        src_lines = []
        seen = set()
        for d in docs:
            m = d.metadata or {}
            key = (m.get("source","?"), m.get("page","?"))
            if key in seen: continue
            seen.add(key)
            base = os.path.basename(m.get("source","?"))
            page = m.get("page","?")
            coll = m.get("collection","")
            full = NIKAYA_FULL.get(coll, coll) if coll else ""
            src_lines.append(f"- {base} (page {page})" + (f"  [{full}]" if full else ""))
        sources_md = "### Sources\n" + ("\n".join(src_lines) if src_lines else "_(none)_")
        return expand_citations(out), sources_md
    except Exception as e:
        return f"**Error:** {e}", ""

with gr.Blocks(title="PaLi-CANON") as app:
    gr.Markdown("# 🪷 PaLi-CANON — Local Pāli Canon Assistant")
    with gr.Row():
        q = gr.Textbox(label="Ask anything (grounded in your local Canon PDFs)", lines=3, placeholder="e.g., Outline Satipaṭṭhāna with citations")
    with gr.Row():
        go = gr.Button("Ask pali")
    out = gr.Markdown(label="Answer", elem_id="answer")
    src = gr.Markdown(label="Sources", elem_id="sources")
    go.click(fn=answer, inputs=q, outputs=[out, src])

if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7860)
