# generate_full_workbook.py
import os
import re
import time
from planner import plan
from retriever import retrieve
from synthesizer import synthesize_workbook_entry

# 1. Copied from app.py: The full 365-day curriculum
CURRICULUM = {
    "Month 1": {
        "Week 1": {
            "Day 1": "The Four Sights",
            "Day 2": "The Palace Life",
            "Day 3": "The Encounter with Old Age",
            "Day 4": "The Encounter with Sickness",
            "Day 5": "The Encounter with Death",
            "Day 6": "The Encounter with the Ascetic",
            "Day 7": "Reflection on the Human Condition",
        },
        "Week 2": {
            "Day 1": "Leaving Behind the Palace",
            "Day 2": "Meeting the Teachers Āḷāra and Uddaka",
            "Day 3": "Mastery and Dissatisfaction",
            "Day 4": "The Six Years of Austerity",
            "Day 5": "The Middle Way Discovered",
            "Day 6": "The River Nerañjarā",
            "Day 7": "The Seat Beneath the Bodhi Tree",
        },
        "Week 3": {
            "Day 1": "The Challenge of Māra",
            "Day 2": "The Moment of Awakening",
            "Day 3": "The Realization of the Four Noble Truths",
            "Day 4": "The Joy of Liberation",
            "Day 5": "The Decision to Teach",
            "Day 6": "The Journey to Bārāṇasī",
            "Day 7": "Meeting the Five Ascetics",
        },
        "Week 4": {
            "Day 1": "The First Turning of the Wheel",
            "Day 2": "Understanding Dukkha",
            "Day 3": "Understanding the Origin of Dukkha",
            "Day 4": "Understanding the Cessation of Dukkha",
            "Day 5": "Understanding the Path Leading to Cessation",
            "Day 6": "The Eightfold Path Overview",
            "Day 7": "The Noble Truths and Daily Life",
        },
        "Week 5": {
            "Day 1": "The Refuge in Buddha, Dhamma, Sangha",
            "Day 2": "Reflection: The Awakening Within",
        },
    },
    "Month 2": {
        "Week 1": {
            "Day 1": "The Mind as Forerunner",
            "Day 2": "Thought Shapes Experience",
            "Day 3": "The Power of Intention",
            "Day 4": "The Stream of Consciousness",
            "Day 5": "Mental Habit and Conditioning",
            "Day 6": "Cultivating Right Thought",
            "Day 7": "The Nature of Wholesome Roots",
        },
        "Week 2": {
            "Day 1": "The Nature of Unwholesome Roots",
            "Day 2": "Greed and the Fire of Desire",
            "Day 3": "Hatred and the Poisoned Heart",
            "Day 4": "Delusion and Confusion of View",
            "Day 5": "Replacing Unwholesome Roots",
            "Day 6": "The Three Trainings Overview",
            "Day 7": "Training in Virtue",
        },
        "Week 3": {
            "Day 1": "Training in Concentration",
            "Day 2": "Training in Wisdom",
            "Day 3": "Balancing the Three Trainings",
            "Day 4": "The Role of Effort",
            "Day 5": "The Nature of Restraint",
            "Day 6": "Guarding the Senses",
            "Day 7": "Moderation in Eating",
        },
        "Week 4": {
            "Day 1": "Wakefulness and Discipline",
            "Day 2": "Reflection and Mindfulness",
            "Day 3": "The Simile of the Saw",
            "Day 4": "The Strength of Patience",
            "Day 5": "The Simile of the Wild Colt",
            "Day 6": "The Power of Resolve",
            "Day 7": "Reflection: The Tamed Heart",
        },
    },
    "Month 3": {
        "Week 1": {
            "Day 1": "The Nature of Loving-Kindness",
            "Day 2": "The Boundless Qualities",
            "Day 3": "The Simile of the Mother’s Love",
            "Day 4": "Mettā Toward Oneself",
            "Day 5": "Mettā Toward Friends",
            "Day 6": "Mettā Toward Strangers",
            "Day 7": "Mettā Toward the Difficult",
        },
        "Week 2": {
            "Day 1": "Mettā for All Beings Everywhere",
            "Day 2": "Obstacles to Loving-Kindness",
            "Day 3": "Expanding the Heart",
            "Day 4": "Compassion (Karuṇā) Defined",
            "Day 5": "Seeing Suffering Clearly",
            "Day 6": "Responding with Compassion",
            "Day 7": "The Balance Between Pity and Strength",
        },
        "Week 3": {
            "Day 1": "Karuṇā in Action",
            "Day 2": "The Great Monkey King",
            "Day 3": "Sympathetic Joy (Muditā)",
            "Day 4": "Rejoicing in Others’ Merit",
            "Day 5": "Freedom from Envy",
            "Day 6": "The Joy of Shared Goodness",
            "Day 7": "Muditā and Generosity",
        },
        "Week 4": {
            "Day 1": "Equanimity (Upekkhā)",
            "Day 2": "The Calm of the Balanced Heart",
            "Day 3": "Upekkhā and Wisdom",
            "Day 4": "Detachment Without Indifference",
            "Day 5": "The Four Brahmavihāras in Harmony",
            "Day 6": "The Story of Meghiya",
            "Day 7": "Friendship as Spiritual Support",
        },
        "Week 5": {
            "Day 1": "The Value of Companionship",
            "Day 2": "Stories of Compassionate Friends",
            "Day 3": "Reflection: The Boundless Heart",
        },
    },
    "Month 4": {
        "Week 1": {
            "Day 1": "The Impermanent Nature of All Things",
            "Day 2": "The Buddha’s Insight into Change",
            "Day 3": "The Simile of the River",
            "Day 4": "Impermanence in the Body",
            "Day 5": "Impermanence in Feelings",
            "Day 6": "Impermanence in Thoughts",
            "Day 7": "Impermanence in Relationships",
        },
        "Week 2": {
            "Day 1": "Impermanence in the World",
            "Day 2": "Contemplating Arising and Passing Away",
            "Day 3": "Dukkha — The Unsatisfactory Nature of Life",
            "Day 4": "The Burden of Craving",
            "Day 5": "The Tension of Desire",
            "Day 6": "The Pain of Loss",
            "Day 7": "The Unease of Becoming",
        },
        "Week 3": {
            "Day 1": "The Unsatisfactory Nature of Pleasure",
            "Day 2": "Seeing the Source of Discontent",
            "Day 3": "Dukkha and the Four Noble Truths",
            "Day 4": "Anattā — The Absence of Ownership",
            "Day 5": "The Illusion of “I” and “Mine”",
            "Day 6": "The Five Aggregates as Empty Process",
            "Day 7": "The Chariot Simile",
        },
        "Week 4": {
            "Day 1": "Seeing Without a Seer",
            "Day 2": "Freedom from Identity View",
            "Day 3": "The Anattalakkhaṇa Sutta",
            "Day 4": "The Release of Letting Go",
            "Day 5": "The Story of Bāhiya Dārucīriya",
            "Day 6": "Understanding Direct Perception",
            "Day 7": "The Simile of the Snake",
        },
        "Week 5": {
            "Day 1": "Letting Go of Clinging",
            "Day 2": "Peace in the Flow of Change",
            "Day 3": "Reflection: Seeing Clearly",
        },
    },
    "Month 5": {
        "Week 1": {
            "Day 1": "Establishing Mindfulness",
            "Day 2": "Knowing the Body as Body",
            "Day 3": "Mindfulness of Breathing",
            "Day 4": "Awareness in Posture",
            "Day 5": "Mindfulness in Movement",
            "Day 6": "The Body as a Field of Practice",
            "Day 7": "The Cemetery Contemplations",
        },
        "Week 2": {
            "Day 1": "The Fragility of Life",
            "Day 2": "Mindfulness of Feelings (Vedanānupassanā)",
            "Day 3": "Pleasant, Painful, and Neutral Feelings",
            "Day 4": "How Feeling Leads to Craving",
            "Day 5": "Meeting Feelings with Equanimity",
            "Day 6": "Understanding the Chain: Feeling → Craving → Clinging",
            "Day 7": "Mindfulness of Mind (Cittānupassanā)",
        },
        "Week 3": {
            "Day 1": "Recognizing Greedy and Ungreedy Mind",
            "Day 2": "Recognizing Hateful and Non-hateful Mind",
            "Day 3": "Recognizing Deluded and Clear Mind",
            "Day 4": "Observing Change in the Mind",
            "Day 5": "The Mirror of Awareness",
            "Day 6": "Mindfulness of Dhammas (Dhammānupassanā)",
            "Day 7": "Contemplating the Five Hindrances",
        },
        "Week 4": {
            "Day 1": "Contemplating the Five Aggregates",
            "Day 2": "Contemplating the Six Sense Bases",
            "Day 3": "Contemplating the Seven Factors of Enlightenment",
            "Day 4": "Contemplating the Four Noble Truths",
            "Day 5": "The Satipaṭṭhāna Sutta",
            "Day 6": "The Power of Continuous Awareness",
            "Day 7": "Clear Comprehension (Sampajañña)",
        },
        "Week 5": {
            "Day 1": "Mindfulness in Daily Action",
            "Day 2": "The Present Moment as Refuge",
            "Day 3": "Reflection: The Foundation of Awareness",
        },
    },
    "Month 6": {
        "Week 1": {
            "Day 1": "The Principle of Conditionality",
            "Day 2": "This Arises, That Arises",
            "Day 3": "The Twelve Links of Dependent Origination",
            "Day 4": "Ignorance (Avijjā) as the First Link",
            "Day 5": "Volitional Formations (Saṅkhārā)",
            "Day 6": "Consciousness (Viññāṇa)",
            "Day 7": "Name-and-Form (Nāma-Rūpa)",
        },
        "Week 2": {
            "Day 1": "The Six Sense Bases (Saḷāyatana)",
            "Day 2": "Contact (Phassa)",
            "Day 3": "Feeling (Vedanā)",
            "Day 4": "Craving (Taṇhā)",
            "Day 5": "Clinging (Upādāna)",
            "Day 6": "Becoming (Bhava)",
            "Day 7": "Birth (Jāti)",
        },
        "Week 3": {
            "Day 1": "Aging and Death (Jarāmaraṇa)",
            "Day 2": "The Full Cycle of Dukkha",
            "Day 3": "The Cessation of the Chain",
            "Day 4": "Ignorance and Insight",
            "Day 5": "Craving and the Fire Sermon",
            "Day 6": "The Simile of the City",
            "Day 7": "The Simile of the Stick",
        },
        "Week 4": {
            "Day 1": "Seeing the Middle Way",
            "Day 2": "The Weaver’s Daughter",
            "Day 3": "The Law of Cause and Effect",
            "Day 4": "Reflection on Karma and Intention",
            "Day 5": "Understanding Conditional Arising in Daily Life",
            "Day 6": "Dependent Origination and the Self",
            "Day 7": "Cessation as Freedom",
        },
        "Week 5": {
            "Day 1": "The Path to Liberation through Insight",
            "Day 2": "Reflection: The Web of Causality",
        },
    },
    "Month 7": {
        "Week 1": {
            "Day 1": "The Lay Follower’s Virtue",
            "Day 2": "The Joy of Giving (Dāna)",
            "Day 3": "Generosity as Freedom from Attachment",
            "Day 4": "The Field of Merit",
            "Day 5": "Sharing Merit with Others",
            "Day 6": "The Value of Simplicity",
            "Day 7": "The Ethics of Livelihood",
        },
        "Week 2": {
            "Day 1": "Right Livelihood and Compassion",
            "Day 2": "Honest Speech and Integrity",
            "Day 3": "The Sigālovāda Sutta",
            "Day 4": "Duties Toward Parents",
            "Day 5": "Duties Toward Teachers",
            "Day 6": "Duties Toward Family",
            "Day 7": "Duties Toward Friends",
        },
        "Week 3": {
            "Day 1": "Duties Toward Servants and Workers",
            "Day 2": "Duties Toward Monastics",
            "Day 3": "Social Harmony Through Right Conduct",
            "Day 4": "The Five Powers of the Trainee",
            "Day 5": "Faith (Saddhā) as Power",
            "Day 6": "Energy (Viriya) as Power",
            "Day 7": "Mindfulness (Sati) as Power",
        },
        "Week 4": {
            "Day 1": "Concentration (Samādhi) as Power",
            "Day 2": "Wisdom (Paññā) as Power",
            "Day 3": "The Story of Anāthapiṇḍika",
            "Day 4": "The Virtue of Contentment",
            "Day 5": "Family Life as Practice",
            "Day 6": "The Generous Heart in Community",
            "Day 7": "The Power of Service",
        },
        "Week 5": {
            "Day 1": "The Joy of Righteous Action",
            "Day 2": "The Layperson’s Refuge",
            "Day 3": "Reflection: The Householder’s Path",
        },
    },
    "Month 8": {
        "Week 1": {
            "Day 1": "The Nature of Māra",
            "Day 2": "The Temptations of Power and Pleasure",
            "Day 3": "Recognizing Māra in Daily Life",
            "Day 4": "Māra as Doubt and Fear",
            "Day 5": "Māra as Self-View",
            "Day 6": "Māra as Complacency",
            "Day 7": "The Māra Saṃyutta",
        },
        "Week 2": {
            "Day 1": "Overcoming Māra with Mindfulness",
            "Day 2": "The Five Hindrances Overview",
            "Day 3": "Sensual Desire — The Sweet Trap",
            "Day 4": "The Weight of Ill Will",
            "Day 5": "Sloth and Torpor — The Fog of the Mind",
            "Day 6": "Restlessness and Worry — The Agitated Heart",
            "Day 7": "Skeptical Doubt — The Divider of Energy",
        },
        "Week 3": {
            "Day 1": "Recognizing Hindrances as Temporary States",
            "Day 2": "Skillful Means to Uproot Hindrances",
            "Day 3": "Replacing Hindrances with Enlightenment Factors",
            "Day 4": "The Factor of Mindfulness",
            "Day 5": "The Factor of Investigation",
            "Day 6": "The Factor of Energy",
            "Day 7": "The Factor of Joy",
        },
        "Week 4": {
            "Day 1": "The Factor of Tranquility",
            "Day 2": "The Factor of Concentration",
            "Day 3": "The Factor of Equanimity",
            "Day 4": "The Balance of the Seven Factors",
            "Day 5": "Fear and the Way Through It",
            "Day 6": "The Story of the Māra Temptations",
            "Day 7": "The Courage of Awareness",
        },
        "Week 5": {
            "Day 1": "Victory Through Compassion",
            "Day 2": "Reflection: Overcoming Māra",
        },
    },
    "Month 9": {
        "Week 1": {
            "Day 1": "The Law of Kamma",
            "Day 2": "Volition as the Seed of Action",
            "Day 3": "Wholesome and Unwholesome Kamma",
            "Day 4": "The Weight of Intention",
            "Day 5": "Immediate and Delayed Results of Action",
            "Day 6": "The Simile of the Salt Crystal",
            "Day 7": "How Kamma Ripens",
        },
        "Week 2": {
            "Day 1": "Conditions that Shape Results",
            "Day 2": "Freedom Within Conditioning",
            "Day 3": "The Dynamics of Moral Choice",
            "Day 4": "Rebirth as Continuity of Process",
            "Day 5": "The Stream of Becoming",
            "Day 6": "The Ten Realms of Existence",
            "Day 7": "The Human Realm as Opportunity",
        },
        "Week 3": {
            "Day 1": "The Heavenly and Hellish Realms",
            "Day 2": "The Nature of Conscious Continuity",
            "Day 3": "The Buddha’s Insight into Past Lives",
            "Day 4": "Dependent Arising and Rebirth",
            "Day 5": "The Wheel of Existence (Saṃsāra)",
            "Day 6": "The Story of Magha",
            "Day 7": "The Jātaka Tales as Moral Mirrors",
        },
        "Week 4": {
            "Day 1": "The Bodhisatta’s Resolve",
            "Day 2": "Lessons from the Vessantara Jātaka",
            "Day 3": "The Power of Intention Across Lifetimes",
            "Day 4": "The Kamma of Speech",
            "Day 5": "The Kamma of Thought",
            "Day 6": "The Kamma of Livelihood",
            "Day 7": "The End of Kamma — Liberation from Becoming",
        },
        "Week 5": {
            "Day 1": "Seeing Beyond Reward and Punishment",
            "Day 2": "Reflection: The Law of Kamma",
        },
    },
    "Month 10": {
        "Week 1": {
            "Day 1": "The Purpose of Concentration",
            "Day 2": "Gathering the Mind",
            "Day 3": "The Simile of the Archer",
            "Day 4": "The First Jhāna — Joy Born of Seclusion",
            "Day 5": "The Second Jhāna — Joy Born of Concentration",
            "Day 6": "The Third Jhāna — Equanimous Pleasure",
            "Day 7": "The Fourth Jhāna — Purity of Equanimity",
        },
        "Week 2": {
            "Day 1": "The Stability of One-Pointedness",
            "Day 2": "The Role of Mindfulness in Concentration",
            "Day 3": "The Balance of Energy and Calm",
            "Day 4": "The Hindrances as Distractions from Stillness",
            "Day 5": "The Simile of the Lute",
            "Day 6": "The Simile of the Lamp in a Still Place",
            "Day 7": "The Joy of Tranquility",
        },
        "Week 3": {
            "Day 1": "The Difference Between Calm and Stagnation",
            "Day 2": "The Relationship Between Samatha and Vipassanā",
            "Day 3": "Insight Arising from Collected Mind",
            "Day 4": "The Beauty of a Settled Heart",
            "Day 5": "Signs of Concentration (Nimitta)",
            "Day 6": "Maintaining Jhāna in Daily Life",
            "Day 7": "The Release of Subtle Attachment",
        },
        "Week 4": {
            "Day 1": "Equanimity as Fruition",
            "Day 2": "The Perception of Light",
            "Day 3": "The Power of Silence",
            "Day 4": "The Happiness of Solitude",
            "Day 5": "The Buddha’s Delight in Meditation",
            "Day 6": "Concentration as a Foundation for Insight",
            "Day 7": "The Union of Calm and Wisdom",
        },
        "Week 5": {
            "Day 1": "The Fruit of Meditative Joy",
            "Day 2": "The Mind Like a Clear Lake",
            "Day 3": "Reflection: The Peace of Stillness",
        },
    },
    "Month 11": {
        "Week 1": {
            "Day 1": "The Meaning of Sāmaññaphala — Fruits of the Contemplative Life",
            "Day 2": "The Gradual Training — Overview",
            "Day 3": "The Layperson and the Stream-Enterer",
            "Day 4": "The Path of the Once-Returner",
            "Day 5": "The Path of the Non-Returner",
            "Day 6": "The Path of the Arahant",
            "Day 7": "Virtue as the First Fruit",
        },
        "Week 2": {
            "Day 1": "Serenity as the Second Fruit",
            "Day 2": "Insight as the Third Fruit",
            "Day 3": "The Joy of Blamelessness",
            "Day 4": "The Peace of Restraint",
            "Day 5": "The Happiness of Contentment",
            "Day 6": "The End of Inner Conflict",
            "Day 7": "The Dhamma Mirror",
        },
        "Week 3": {
            "Day 1": "The Fruits of Generosity",
            "Day 2": "The Fruits of Loving-Kindness",
            "Day 3": "The Fruits of Mindfulness",
            "Day 4": "The Fruits of Wisdom",
            "Day 5": "The Noble Friend (Kalyāṇa-mitta)",
            "Day 6": "Confidence in the Dhamma — The Lion’s Roar",
            "Day 7": "The Confidence of the Stream-Enterer",
        },
        "Week 4": {
            "Day 1": "The Assurance of Non-Regression",
            "Day 2": "The Simile of the Mountain Peak",
            "Day 3": "The Story of Citta the Householder",
            "Day 4": "The Story of Visākhā",
            "Day 5": "The Joy of the Noble Ones",
            "Day 6": "The Noble Silence",
            "Day 7": "The Fragrance of Virtue",
        },
        "Week 5": {
            "Day 1": "The Fruits Beyond Measure",
            "Day 2": "Reflection: Living the Fruits of the Path",
        },
    },
    "Month 12": {
        "Week 1": {
            "Day 1": "The Journey to Kusinārā",
            "Day 2": "The Illness of the Tathāgata",
            "Day 3": "The Last Meal and Cunda the Smith",
            "Day 4": "The Compassion of Allowing Cunda’s Offering",
            "Day 5": "The Final Instructions to the Bhikkhus",
            "Day 6": "The Last Words to Ānanda",
            "Day 7": "The Buddha’s Final Teaching: “Be Islands Unto Yourselves”",
        },
        "Week 2": {
            "Day 1": "The Buddha’s Last Night Under the Sāla Trees",
            "Day 2": "The Passing into Parinibbāna",
            "Day 3": "The Earthquake and Celestial Tributes",
            "Day 4": "The Lamentation of the Mallas",
            "Day 5": "The Division of the Relics",
            "Day 6": "The Building of Stūpas",
            "Day 7": "The Legacy of the Dhamma",
        },
        "Week 3": {
            "Day 1": "The Council at Rājagaha",
            "Day 2": "The Preservation of the Teachings",
            "Day 3": "The Continuity of the Sangha",
            "Day 4": "The Arising of Great Disciples",
            "Day 5": "Mahākassapa’s Leadership",
            "Day 6": "Ānanda’s Wisdom and Memory",
            "Day 7": "Discourses of the Bhikkhunīs",
        },
        "Week 4": {
            "Day 1": "The Liberation of Kisāgotamī",
            "Day 2": "The Courage of Mahāpajāpati Gotamī",
            "Day 3": "The Example of Bhaddā Kuṇḍalakesā",
            "Day 4": "The Voices of the Arahants",
            "Day 5": "The Nature of True Freedom",
            "Day 6": "Nibbāna — The Unconditioned Peace",
            "Day 7": "The End of Craving",
        },
        "Week 5": {
            "Day 1": "The Stillness Beyond Birth and Death",
            "Day 2": "The Ever-Living Dhamma",
            "Day 3": "End of Year Reflection: Turning the Wheel Again",
        },
    },
}

# 2. This function is adapted from app.py
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

# 3. This is the main generator function (NOW MORE VERBOSE)
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

# 4. This makes the script runnable from the command line
if __name__ == "__main__":
    generate_full_workbook()
