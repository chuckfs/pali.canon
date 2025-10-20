# app.py
import gradio as gr
from planner import plan
from retriever import retrieve
from synthesizer import synthesize, synthesize_workbook_entry # Import our new function
from indexer import build_index

# --- Workbook Generation Logic ---
# This curriculum can be expanded to include all 12 months.
CURRICULUM = {
    "Month 1": {
        "Week 1": "The Buddha’s life & awakening",
        "Week 2": "The Four Noble Truths",
        "Week 3": "The Eightfold Path overview",
        "Week 4": "Refuge & intention",
        "Week 5": "Reflection on precepts",
    },
    "Month 2": {
        "Week 6": "Mind and its training",
        "Week 7": "Wholesome vs unwholesome roots",
        "Week 8": "Restraint and awareness",
        "Week 9": "The Simile of the Saw",
        "Week 10": "Story reflection — The Great Monkey King",
    }
    # Add the rest of your curriculum here...
}

def generate_workbook(month: int, week: int):
    """
    Generates a workbook entry for a given month and week from the curriculum.
    """
    # Construct the keys to look up the topic in the curriculum
    month_str = f"Month {int(month)}"
    week_str = f"Week {int(week)}"
    topic = CURRICULUM.get(month_str, {}).get(week_str)

    if not topic:
        return f"## Topic Not Found\n\nCould not find a topic for Month {int(month)}, Week {int(week)}. Please check the curriculum."

    # Use your existing planner and retriever to find relevant passages
    p = plan(topic)
    hits = retrieve(p)

    if not hits:
        return f"## No Passages Found\n\nCould not find any relevant passages for the topic: '{topic}'. You may need to broaden the topic or re-index your data."

    # Use the new synthesizer to format the workbook entry
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
                                 examples=["What does the Buddha say about craving?", "Explain the simile of the saw.", "Where is the Kālāma Sutta found?"])

            with gr.TabItem("Workbook Generator"):
                gr.Markdown("## Weekly Workbook Generator")
                with gr.Row():
                    month_input = gr.Number(label="Month", value=1, minimum=1, maximum=12, step=1)
                    week_input = gr.Number(label="Week", value=1, minimum=1, maximum=60, step=1)
                generate_btn = gr.Button("Generate Workbook Entry", variant="primary")
                workbook_output = gr.Markdown()

                generate_btn.click(
                    fn=generate_workbook,
                    inputs=[month_input, week_input],
                    outputs=workbook_output,
                )

        with gr.Row():
            btn_index = gr.Button("Build / Refresh Index")

        def _do_index():
            build_index()
            # Use gr.Info for a temporary, non-blocking notification
            gr.Info("Index build started. This may take a while.")
            return None # No component update needed

        btn_index.click(fn=_do_index, outputs=None)

    return demo

if __name__ == "__main__":
    demo = ui()
    demo.launch()
