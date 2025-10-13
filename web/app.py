# web/app.py
import os, re, gradio as gr
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_chroma import Chroma
from langchain.prompts import PromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain

HOME = os.path.expanduser("~")
PERSIST_DIR = os.path.expanduser(os.environ.get("LOTUS_CHROMA_DIR", f"{HOME}/PaLi-CANON/chroma"))
COLLECTION  = os.environ.get("LOTUS_CHROMA_COLLECTION", "lotus_canon")
EMBED_MODEL = os.environ.get("LOTUS_EMBED_MODEL", "nomic-embed-text")

NIKAYA_FULL = {"DN":"Dīgha Nikāya","MN":"Majjhima Nikāya","SN":"Saṃyutta Nikāya","AN":"Aṅguttara Nikāya","KN":"Khuddaka Nikāya"}
ABBR_RX = re.compile(r'\b(DN|MN|SN|AN|KN)\s+(\d+(?:\.\d+)?)\b')
def expand_citations(t:str)->str: return ABBR_RX.sub(lambda m: f"{NIKAYA_FULL[m.group(1)]} ({m.group(1)} {m.group(2)})", t)

PROMPT = PromptTemplate.from_template(
    "You are a careful Theravāda teacher. Use ONLY the provided Pāli Canon context.\n"
    "Return headings, bullets, brief *italic* quotes with FULL citations, plus a 'Suggested Readings' list.\n\n"
    "Question:\n{question}\n\nContext:\n{context}\n"
)

def build_db():
    emb = OllamaEmbeddings(model=EMBED_MODEL)
    return Chroma(embedding_function=emb, persist_directory=PERSIST_DIR, collection_name=COLLECTION)

def retrieve(db, q:str):
    retr = db.as_retriever(search_type="mmr", search_kwargs={"k":18, "fetch_k":80, "lambda_mult":0.75})
    docs = retr.invoke(q) or db.as_retriever(search_type="similarity", search_kwargs={"k":25}).invoke(q)
    return docs

def ask_pali(history, message):
    db = build_db(); docs = retrieve(db, message)
    llm = OllamaLLM(model="mistral")
    chain = create_stuff_documents_chain(llm, PROMPT)
    out = chain.invoke({"question": message, "context": docs})
    out = expand_citations(out)

    # Sources
    src = []
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
        src.append(f"- **{base}** — page {page}" + (f" · *{full}*" if full else ""))
    answer = out + ("\n\n---\n**Sources**\n" + "\n".join(src) if src else "\n\n---\n**Sources**\n_(none)_")
    history = history + [[message, answer]]
    return history, gr.update(value="")

css = """
#app .gradio-container {max-width: 900px !important;}
#app h1 {font-family: ui-serif, Georgia, serif;}
#app .source-note {opacity:.8; font-size:.9em;}
"""

with gr.Blocks(theme=gr.themes.Soft(primary_hue="purple"), css=css, title="PaLi-CANON", elem_id="app") as demo:
    gr.Markdown("# 🪷 PaLi-CANON — Local Pāli Canon Assistant\nUse your own indexed Canon to get grounded lessons with citations.")
    chat = gr.Chatbot(height=520, avatar_images=(None, None), show_copy_button=True)
    msg  = gr.Textbox(placeholder="e.g., Outline Satipaṭṭhāna with full citations…", label="Ask pali")
    btn  = gr.Button("Ask", variant="primary")
    btn.click(ask_pali, [chat, msg], [chat, msg]); msg.submit(ask_pali, [chat, msg], [chat, msg])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
