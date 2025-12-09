# app.py
import gradio as gr
import json
import os
from planner import plan
from retriever import retrieve
from synthesizer import synthesize, synthesize_workbook_entry
from indexer import build_index

# --- Load Curriculum ---
# Uses a relative path to data/curriculum.json
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CURRICULUM_PATH = os.path.join(BASE_DIR, "data", "curriculum.json")

try:
    with open(CURRICULUM_PATH, "r", encoding="utf-8") as f:
        CURRICULUM = json.load(f)
except FileNotFoundError:
    print(f"Warning: Curriculum file not found at {CURRICULUM_PATH}")
    CURRICULUM = {}

def generate_workbook(month: int, week: int, day: int):
    """
    Generates a workbook entry for a given month, week, and day.
    """
    # Construct the keys to look up the daily topic
    month_str = f"Month {int(month)}"
    week_str = f"Week {int(week)}"
    day_str = f"Day {int(day)}"
    
    # Nested .get() calls to safely access the topic
    topic = CURRICULUM.get(month_str, {}).get(week_str, {}).get(day_str)

    if not topic:
        return f"## Topic Not Found\n\nCould not find a topic for Month {int(month)}, Week {int(week)}, Day {int(day)}. Please check the curriculum."

    # Use your existing planner and retriever
    p = plan(topic)
    hits = retrieve(p)

    if not hits:
        return f"## No Passages Found\n\nCould not find any relevant passages for the topic: '{topic}'. You may need to broaden the topic or re-index your data."

    # Use the synthesizer to format the daily workbook entry
    return synthesize_workbook_entry(topic, hits)

# --- Gradio UI ---

def ask(q: str, history):
    p = plan(q)
    hits = retrieve(p)
    return synthesize(q, hits)

def ui():
    with gr.Blocks(title="pali.canon") as demo:
        gr.Markdown("# pali.canon — Canon-grounded Q&A")

        with gr.Tabs():
            with gr.TabItem("Conversational Q&A"):
                gr.ChatInterface(ask,
                                 chatbot=gr.Chatbot(height=500),
                                 textbox=gr.Textbox(placeholder="Ask anything about the Pāli Canon...", container=False, scale=7),
                                 examples=["What does the Buddha say about craving?", "Explain the simile of the saw."])

            with gr.TabItem("Daily Workbook Generator"):
                gr.Markdown("## Daily Workbook Generator")
                with gr.Row():
                    month_input = gr.Number(label="Month", value=1, minimum=1, maximum=12, step=1)
                    week_input = gr.Number(label="Week", value=1, minimum=1, maximum=5, step=1) # Max weeks in a month
                    day_input = gr.Number(label="Day", value=1, minimum=1, maximum=7, step=1) # Max days in a week
                generate_btn = gr.Button("Generate Daily Workbook Entry", variant="primary")
                workbook_output = gr.Markdown()

                generate_btn.click(
                    fn=generate_workbook,
                    inputs=[month_input, week_input, day_input],
                    outputs=workbook_output,
                )

        with gr.Row():
            btn_index = gr.Button("Build / Refresh Index")

        def _do_index():
            build_index()
            gr.Info("Index build started. This may take a while.")
            return None

        btn_index.click(fn=_do_index, outputs=None)

    return demo

if __name__ == "__main__":
    demo = ui()
    demo.launch()
