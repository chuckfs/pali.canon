# app.py
import gradio as gr
from planner import plan
from retriever import retrieve
from synthesizer import synthesize
from indexer import build_index

def ask(q: str, history):
    p = plan(q)
    hits = retrieve(p)
    return synthesize(q, hits)

def ui():
    with gr.Blocks(title="pali.canon") as demo:
        gr.Markdown("# pali.canon — Canon-grounded Q&A")
        with gr.Row():
            btn_index = gr.Button("Build / Refresh Index")
        chat = gr.ChatInterface(ask, type="messages")
        def _do_index():
            build_index()
            return gr.update(value="Index done.")
        btn_index.click(fn=_do_index, outputs=[])
    return demo

if __name__ == "__main__":
    demo = ui()
    demo.launch()