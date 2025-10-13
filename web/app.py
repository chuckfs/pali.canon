# web/app.py
import gradio as gr
import os, time
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_chroma import Chroma
from langchain.prompts import PromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain

HOME = os.path.expanduser("~")
PROJECT = os.path.expanduser(os.environ.get("PALI_PROJECT_ROOT", f"{HOME}/PaLi-CANON"))
PERSIST_DIR = os.path.expanduser(os.environ.get("LOTUS_CHROMA_DIR", f"{PROJECT}/chroma"))
COLLECTION  = os.environ.get("LOTUS_CHROMA_COLLECTION", "lotus_canon")
EMBED_MODEL = os.environ.get("LOTUS_EMBED_MODEL", "nomic-embed-text")
DEFAULT_LLM = os.environ.get("LOTUS_LLM_MODEL", "mistral")

# basic retrieval
def build_db():
    emb = OllamaEmbeddings(model=EMBED_MODEL)
    return Chroma(embedding_function=emb, persist_directory=PERSIST_DIR, collection_name=COLLECTION)

PROMPT = PromptTemplate.from_template(
    "You are a calm Theravāda teacher. Use only the provided context.\n\nQuestion:\n{question}\n\nContext:\n{context}"
)

def ask(question):
    t0 = time.time()
    db = build_db()
    retriever = db.as_retriever(search_type="mmr", search_kwargs={"k":12, "fetch_k":50})
    docs = retriever.invoke(question)
    llm = OllamaLLM(model=DEFAULT_LLM, temperature=0.5)
    chain = create_stuff_documents_chain(llm, PROMPT)
    ans = chain.invoke({"question": question, "context": docs})
    elapsed = f"⏱ {time.time()-t0:.2f}s"
    return f"{ans}\n\n---\n{elapsed}"

# ---------- minimal clean UI ----------
CSS = """
:root {
  color-scheme: light dark;
}
body {
  background-color: Canvas;
  color: CanvasText;
  font-family: system-ui, -apple-system, 'Inter', sans-serif;
}
h1 {
  text-align: center;
  font-weight: 700;
  font-size: 2rem;
  margin-bottom: 1rem;
}
#chatbox {
  max-width: 720px;
  margin: 0 auto;
}
"""

with gr.Blocks(css=CSS, title="PaLi-CANON") as demo:
    gr.Markdown("<h1>PaLi-CANON</h1>")
    chat = gr.ChatInterface(
        fn=lambda message, history: (ask(message), history),
        chatbot=gr.Chatbot(height=500, bubble_full_width=False),
        placeholder="Ask a question about the Pāli Canon...",
        submit_btn="Ask",
        stop_btn="Stop"
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
