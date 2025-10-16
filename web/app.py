#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gradio app for G-RAG-G: query -> planner -> retriever -> synthesizer
Exposes basket/nikāya dropdowns and top_k control.
"""

from __future__ import annotations
import os
import gradio as gr

from planner import plan_query
from retriever import retrieve
from synthesizer import synthesize


APP_TITLE = "pali . canon (chkxd)"
APP_DESC = (
    "🪷 **Pāli Canon — Canon-Grounded Q&A**\n"
    "Ask a question about the Pāli Canon and get grounded answers with page-level citations.\n"
    "Use the Basket/Nikāya controls to guide retrieval, or leave them on **(auto)**."
)

def run_query(q: str, basket_choice: str, nikaya_choice: str, top_k: int, require_citations: bool) -> str:
    q = (q or "").strip()
    if not q:
        return "Please enter a question."

    plan = plan_query(q)
    c = plan.setdefault("constraints", {})
    if basket_choice and basket_choice != "(auto)":
        c["basket"] = basket_choice
    if nikaya_choice and nikaya_choice != "(auto)":
        c["nikaya"] = nikaya_choice

    plan["require_citations"] = bool(require_citations)

    hits = retrieve(plan, top_k=top_k)
    answer = synthesize(q, plan, hits)
    return answer


with gr.Blocks(title=APP_TITLE) as demo:
    gr.Markdown(f"## {APP_TITLE}\n{APP_DESC}")

    with gr.Row():
        q = gr.Textbox(
            label="Question",
            lines=3,
            placeholder="e.g., Where is the Fire Sermon (Ādittapariyāya) and what does it teach?"
        )

    with gr.Row():
        basket = gr.Dropdown(
            choices=["(auto)", "sutta", "vinaya", "abhidhamma"],
            value="(auto)",
            label="Basket"
        )
        nikaya = gr.Dropdown(
            choices=["(auto)", "DN", "MN", "SN", "AN", "KN"],
            value="(auto)",
            label="Nikāya (Sutta collections + KN umbrella)"
        )

    with gr.Row():
        top_k = gr.Slider(minimum=2, maximum=20, step=1, value=int(os.getenv("TOP_K", "8")), label="Top-K (chunks)")
        citations = gr.Checkbox(value=True, label="Append Sources")

    with gr.Row():
        go = gr.Button("Ask", variant="primary")

    out = gr.Markdown(label="Answer")

    go.click(run_query, inputs=[q, basket, nikaya, top_k, citations], outputs=[out])

if __name__ == "__main__":
    # You can override server params with env vars if needed
    demo.launch(
        share=False,
        server_name=os.getenv("GRADIO_SERVER_NAME", "127.0.0.1"),
        server_port=int(os.getenv("GRADIO_SERVER_PORT", "7860"))
    )