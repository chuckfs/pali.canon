# generate_full_workbook.py
import os
import re
import time
import json
from planner import plan
from retriever import retrieve
from synthesizer import synthesize_workbook_entry

# --- Load Curriculum ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CURRICULUM_PATH = os.path.join(BASE_DIR, "data", "curriculum.json")

try:
    with open(CURRICULUM_PATH, "r", encoding="utf-8") as f:
        CURRICULUM = json.load(f)
except FileNotFoundError:
    print(f"Error: Curriculum file not found at {CURRICULUM_PATH}")
    exit(1)

def get_daily_entry(topic: str):
    """
    Generates a single workbook entry for a given topic.
    """
    if not topic:
        return "## Topic Not Found"

    # Use your existing planner and retriever
    p = plan(topic)
    hits = retrieve(p)

    if not hits:
        return f"## No Passages Found\n\nCould not find any relevant passages for the topic: '{topic}'."

    # Use the synthesizer to format the daily workbook entry
    return synthesize_workbook_entry(topic, hits)

def make_safe_filename(topic, day_num_str):
    """Creates a clean filename from the topic string."""
    safe_topic = re.sub(r'[^a-zA-Z0-9 \-]', '', topic).strip()
    safe_topic = re.sub(r'\s+', '_', safe_topic)
    safe_topic = safe_topic[:50]
    return f"Day_{day_num_str}-{safe_topic}.md"

def generate_full_workbook():
    """
    Loops through the entire curriculum and saves each day as a separate file.
    """
    output_dir = "My_Pali_Workbook"
    os.makedirs(output_dir, exist_ok=True)
    
    print("="*70)
    print(f"🪷 STARTING FULL WORKBOOK GENERATION 🪷")
    print(f"Output directory: ./{output_dir}/")
    print("="*70)
    
    start_time = time.time()
    day_counter = 1
    total_files_created = 0

    for month_str, weeks in CURRICULUM.items():
        month_num = int(month_str.split(' ')[1])
        month_dir = os.path.join(output_dir, f"{month_num:02d}-{month_str.replace(' ', '_')}")
        os.makedirs(month_dir, exist_ok=True)
        
        for week_str, days in weeks.items():
            week_num = int(week_str.split(' ')[1])
            week_dir = os.path.join(month_dir, f"{week_num:02d}-{week_str.replace(' ', '_')}")
            os.makedirs(week_dir, exist_ok=True)
            
            for day_str, topic in days.items():
                day_num = int(day_str.split(' ')[1])
                day_num_str = str(day_counter).zfill(3) # Pads with zeros, e.g., 001, 002...
                
                # --- VERBOSE PRINT START ---
                print(f"\nProcessing Day {day_num_str} (M:{month_num} W:{week_num} D:{day_num})")
                print(f"  Topic: {topic}")
                
                # Generate the content
                content = get_daily_entry(topic)
                
                # Create a clean filename
                filename = make_safe_filename(topic, day_num_str)
                filepath = os.path.join(week_dir, filename)
                
                # Save the file
                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(f"# {month_str} - {week_str} - {day_str}\n")
                        f.write(f"## {topic}\n\n")
                        f.write(content)
                    
                    # --- VERBOSE PRINT DONE ---
                    print(f"  [SUCCESS] Day {day_num_str} done. Saved to {filepath}")
                    total_files_created += 1
                    
                except Exception as e:
                    print(f"  [ERROR] FAILED to write file for Day {day_num_str}: {e}")
                
                day_counter += 1

    end_time = time.time()
    total_time = end_time - start_time
    
    # --- VERBOSE PRINT FINISHED ---
    print("\n" + "="*70)
    print(f"✅ WORKBOOK GENERATION COMPLETE! ✅")
    print("="*70)
    print(f"  Total files created: {total_files_created} / 365")
    print(f"  Total time taken: {total_time:.2f} seconds")
    print(f"  All files are located in the '{output_dir}' folder.")
    print("="*70)

if __name__ == "__main__":
    generate_full_workbook()
