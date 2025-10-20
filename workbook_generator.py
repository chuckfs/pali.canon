# workbook_generator.py
import gradio as gr
from planner import plan
from retriever import retrieve
from synthesizer import synthesize_workbook_entry # We'll create this new function

# Your curriculum, structured for the script
CURRICULUM = {
    "Month 1": {
        "Week 1": "The Buddha’s life & awakening",
        "Week 2": "The Four Noble Truths",
        "Week 3": "The Eightfold Path overview",
        "Week 4": "Refuge & intention",
        "Week 5": "Reflection on precepts",
    },
    # ... and so on for the rest of the months
}

def generate_workbook(month: int, week: int):
    """
    Generates a workbook entry for a given month and week.
    """
    week_str = f"Week {week}"
    month_str = f"Month {month}"
    topic = CURRICULUM.get(month_str, {}).get(week_str)

    if not topic:
        return "Topic not found for that month and week."

    print(f"Generating workbook for: {topic}...")

    # Use your existing planner and retriever
    p = plan(topic)
    hits = retrieve(p)

    if not hits:
        return f"Could not find any passages for the topic: {topic}"

    # Use our new synthesizer to format the workbook entry
    return synthesize_workbook_entry(topic, hits)


if __name__ == "__main__":
    # Example of how to run it
    workbook_content = generate_workbook(month=1, week=2)
    with open("workbook_week_2.md", "w") as f:
        f.write(workbook_content)
    print("Workbook for Week 2 generated!")
