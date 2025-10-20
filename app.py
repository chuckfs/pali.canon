# app.py
import gradio as gr
from planner import plan
from retriever import retrieve
from synthesizer import synthesize, synthesize_workbook_entry
from indexer import build_index
import yaml
import os

# --- Workbook Generation Logic ---

def load_curriculum():
    """
    Loads the full 12-month curriculum.
    """
    # This dictionary now contains your complete curriculum.
    # In the future, you could load this from your YAML files.
    CURRICULUM = {
        "Month 1": {
            "Week 1": {"Day 1": "The Buddha’s life & awakening", "Day 2": "The Four Sights", "Day 3": "The Great Renunciation", "Day 4": "The Search for Truth", "Day 5": "The Defeat of Mara", "Day 6": "The Enlightenment", "Day 7": "Weekly Reflection"},
            "Week 2": {"Day 1": "The First Noble Truth", "Day 2": "The Second Noble Truth", "Day 3": "The Third Noble Truth", "Day 4": "The Fourth Noble Truth", "Day 5": "Gratification, Danger, and Escape", "Day 6": "The Nature of Craving", "Day 7": "Weekly Reflection"},
            "Week 3": {"Day 1": "Right View", "Day 2": "Right Intention", "Day 3": "Right Speech", "Day 4": "Right Action", "Day 5": "Right Livelihood", "Day 6": "Right Effort", "Day 7": "Weekly Reflection"},
            "Week 4": {"Day 1": "Refuge in the Buddha", "Day 2": "Refuge in the Dhamma", "Day 3": "Refuge in the Sangha", "Day 4": "The Ratana Sutta", "Day 5": "The Mangala Sutta", "Day 6": "The Power of Intention", "Day 7": "Weekly Reflection"},
            "Week 5": {"Day 1": "The First Precept", "Day 2": "The Second Precept", "Day 3": "The Third Precept", "Day 4": "The Fourth Precept", "Day 5": "The Fifth Precept", "Day 6": "The Kumbha Jātaka", "Day 7": "Weekly Reflection"},
        },
        "Month 2": {
            "Week 6": {"Day 1": "The Mind is the Forerunner", "Day 2": "The Power of Thought", "Day 3": "Training the Mind", "Day 4": "The Unwholesome Roots", "Day 5": "The Wholesome Roots", "Day 6": "The Simile of the Wild Colt", "Day 7": "Weekly Reflection"},
            "Week 7": {"Day 1": "Sīla: Ethical Conduct", "Day 2": "Samādhi: Concentration", "Day 3": "Paññā: Wisdom", "Day 4": "The Simile of the Saw", "Day 5": "The Great Monkey King", "Day 6": "Restraint and Awareness", "Day 7": "Weekly Reflection"},
        },
        "Month 3": {
            "Week 11": {"Day 1": "The Karaṇīyametta Sutta", "Day 2": "The Four Brahmavihāras", "Day 3": "The Meghiya Sutta", "Day 4": "The Value of Friendship", "Day 5": "Stories of Compassion", "Day 6": "Metta Chanting", "Day 7": "Weekly Reflection"},
        },
        "Month 4": {
            "Week 16": {"Day 1": "Anicca: Impermanence", "Day 2": "Dukkha: Suffering", "Day 3": "Anattā: Not-Self", "Day 4": "The Anattalakkhaṇa Sutta", "Day 5": "The Simile of the Chariot", "Day 6": "The Story of Bāhiya Dārucīriya", "Day 7": "Weekly Reflection"},
        },
        "Month 5": {
            "Week 21": {"Day 1": "The Four Right Efforts", "Day 2": "The Satipaṭṭhāna Sutta", "Day 3": "The Fire Sermon", "Day 4": "The Bhikkhunī Saṃyutta", "Day 5": "Mindfulness of Body", "Day 6": "Mindfulness of Feeling", "Day 7": "Weekly Reflection"},
        },
        "Month 6": {
            "Week 26": {"Day 1": "Paṭiccasamuppāda: Dependent Origination", "Day 2": "Kaccāyana on Right View", "Day 3": "The City & The Stick Similes", "Day 4": "The Weaver’s Daughter Story", "Day 5": "Reflection on Causality", "Day 6": "The Path to Liberation", "Day 7": "Weekly Reflection"},
        },
        "Month 7": {
            "Week 31": {"Day 1": "Lay Virtue and Generosity", "Day 2": "The Sigālovāda Sutta", "Day 3": "The Five Powers of the Trainee", "Day 4": "The Story of Anāthapiṇḍika’s Son Kāla", "Day 5": "Communal Harmony", "Day 6": "The Rohiṇī River Story", "Day 7": "Weekly Reflection"},
        },
        "Month 8": {
            "Week 36": {"Day 1": "The Māra Saṃyutta", "Day 2": "The Sixteen Dreams", "Day 3": "The Bhikkhunī Samyutta Revisited", "Day 4": "Māra the Evil One", "Day 5": "Recognizing Hindrances as Māra", "Day 6": "Overcoming Obstacles", "Day 7": "Weekly Reflection"},
        },
        "Month 9": {
            "Week 41": {"Day 1": "The Story of Magha", "Day 2": "The Jackal’s Judgment", "Day 3": "The Sound the Hare Heard", "Day 4": "The Bodhisatta’s Resolve", "Day 5": "Reflection on Kamma", "Day 6": "The Nature of Rebirth", "Day 7": "Weekly Reflection"},
        },
        "Month 10": {
            "Week 46": {"Day 1": "Jhāna Factors", "Day 2": "The Simile of the Lute", "Day 3": "The Nanda Sutta", "Day 4": "The Mahāsamaya Sutta", "Day 5": "Meditative Integration", "Day 6": "Calm and Insight", "Day 7": "Weekly Reflection"},
        },
        "Month 11": {
            "Week 51": {"Day 1": "The Sāmaññaphala Sutta", "Day 2": "The Cūḷahatthipadopama Sutta", "Day 3": "The Lion’s Roar", "Day 4": "Reflections on Arahantship", "Day 5": "Living the Dhamma in Daily Life", "Day 6": "The Gradual Training", "Day 7": "Weekly Reflection"},
        },
        "Month 12": {
            "Week 56": {"Day 1": "The Upasiva Sutta", "Day 2": "The Mahāparinibbāna Sutta", "Day 3": "The Buddha’s Last Days", "Day 4": "Parinibbāna Chanting", "Day 5": "Discourses of the Ancient Nuns", "Day 6": "Freedom Realized", "Day 7": "Year-end Reflection"},
        },
    }
    return CURRICULUM

CURRICULUM = load_curriculum()

def generate_workbook(month: int, week: int, day: int):
    """
    Generates a workbook entry for a given month, week, and day.
    """
    month_str = f"Month {int(month)}"
    week_str = f"Week {int(week)}"
    day_str = f"Day {int(day)}"
    
    topic = CURRICULUM.get(month_str, {}).get(week_str, {}).get(day_str)

    if not topic:
        return f"## Topic Not Found\n\nCould not find a topic for Month {int(month)}, Week {int(week)}, Day {int(day)}. Please check the curriculum."

    p = plan(topic)
    hits = retrieve(p)

    if not hits:
        return f"## No Passages Found\n\nCould not find any relevant passages for the topic: '{topic}'. You may need to broaden the topic or re-index your data."

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
                    week_input = gr.Number(label="Week", value=1, minimum=1, maximum=60, step=1)
                    day_input = gr.Number(label="Day", value=1, minimum=1, maximum=7, step=1)
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
