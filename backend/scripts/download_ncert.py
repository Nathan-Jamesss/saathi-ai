"""
download_ncert.py — Download NCERT text corpus from HuggingFace dataset.

Dataset: KadamParth/Ncert_dataset (Classes 6–12, pre-extracted text)

Usage:
    python scripts/download_ncert.py

Output:
    data/ncert/<class>_<subject>.json  — one file per class+subject

This script only needs to run once. The output feeds into build_index.py.
"""

import os
import json
import sys

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "ncert")
os.makedirs(DATA_DIR, exist_ok=True)


def download_from_huggingface():
    try:
        from datasets import load_dataset
    except ImportError:
        print("ERROR: Install 'datasets' first: pip install datasets")
        sys.exit(1)

    print("Downloading KadamParth/Ncert_dataset from HuggingFace...")
    try:
        ds = load_dataset("KadamParth/Ncert_dataset", split="train")
    except Exception as e:
        print(f"HuggingFace download failed: {e}")
        print("Falling back to sample data...")
        create_sample_data()
        return

    # Group by grade + subject (actual HuggingFace field names: grade, subject, Topic, Explanation)
    grouped = {}
    for item in ds:
        grade   = str(item.get("grade") or "unknown")
        subject = (item.get("subject") or "unknown").lower().replace(" ", "_")
        key = f"{grade}_{subject}"
        if key not in grouped:
            grouped[key] = []
        parts = []
        if item.get("Topic"):
            parts.append(f"Topic: {item['Topic']}")
        if item.get("Explanation"):
            parts.append(item["Explanation"])
        if item.get("Question") and item.get("Answer"):
            parts.append(f"Q: {item['Question']} A: {item['Answer']}")
        grouped[key].append({
            "class":   item.get("grade"),
            "subject": subject,
            "chapter": item.get("Topic", ""),
            "text":    "\n".join(parts),
        })

    for key, items in grouped.items():
        out_path = os.path.join(DATA_DIR, f"{key}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        print(f"  Saved {len(items)} items -> {out_path}")

    print(f"\nDownload complete. {len(grouped)} files saved to {DATA_DIR}")


def create_sample_data():
    """Create minimal sample NCERT-style data for testing when HuggingFace is unavailable."""
    samples = [
        {
            "class": 9, "subject": "science",
            "chapter": "Matter in Our Surroundings",
            "text": """Matter is anything that has mass and occupies space. Matter is made up of tiny particles called atoms and molecules.
States of Matter: Matter exists in three states — solid, liquid, and gas.
In solids, particles are tightly packed and have definite shape and volume.
In liquids, particles are loosely packed and have definite volume but no definite shape.
In gases, particles are far apart and have neither definite shape nor definite volume.
Changes of State: Melting is the change from solid to liquid. Boiling is the change from liquid to gas.
Evaporation is the change from liquid to gas at the surface, below the boiling point.
The rate of evaporation increases with temperature, surface area, and wind speed.""",
        },
        {
            "class": 9, "subject": "science",
            "chapter": "Is Matter Around Us Pure",
            "text": """A pure substance consists of a single type of particle. Elements and compounds are pure substances.
A mixture contains two or more substances. Mixtures can be homogeneous (uniform throughout) or heterogeneous (not uniform).
Photosynthesis: Plants make food using sunlight, water (H2O), and carbon dioxide (CO2) to produce glucose (C6H12O6) and oxygen (O2).
The equation is: 6CO2 + 6H2O → C6H12O6 + 6O2
Chlorophyll is the green pigment in plants that absorbs sunlight for photosynthesis.
Photosynthesis occurs in the chloroplasts of plant cells.""",
        },
        {
            "class": 9, "subject": "science",
            "chapter": "The Fundamental Unit of Life",
            "text": """The cell is the basic structural and functional unit of life. All living organisms are made of cells.
Cell theory states that all organisms are made of cells, the cell is the basic unit of life, and all cells arise from pre-existing cells.
Parts of a cell: Cell membrane (plasma membrane), cytoplasm, nucleus, mitochondria, endoplasmic reticulum, Golgi apparatus.
The mitochondria is called the powerhouse of the cell because it produces energy (ATP) through cellular respiration.
The nucleus is the control center of the cell containing DNA and chromosomes.""",
        },
        {
            "class": 10, "subject": "science",
            "chapter": "Life Processes",
            "text": """Life processes are the basic processes necessary for maintaining life: nutrition, respiration, transportation, excretion.
Nutrition: Autotrophs make their own food (plants via photosynthesis). Heterotrophs depend on other organisms.
Photosynthesis formula: 6CO2 + 6H2O + light energy → C6H12O6 + 6O2
Respiration: Process of releasing energy from food. Aerobic respiration uses oxygen. Anaerobic respiration occurs without oxygen.
Transportation in plants: Xylem transports water and minerals from roots to leaves. Phloem transports food from leaves to other parts.""",
        },
        {
            "class": 10, "subject": "science",
            "chapter": "Electricity",
            "text": """Electric current is the flow of electric charge. It is measured in Amperes (A).
Ohm's Law: V = IR, where V is voltage (volts), I is current (amperes), R is resistance (ohms).
Resistance: Opposition to flow of current. Depends on length, cross-sectional area, and material of conductor.
Series circuit: Components connected end-to-end. Same current flows through all. Total resistance = R1 + R2 + R3.
Parallel circuit: Components connected across same two points. Same voltage across all. 1/R_total = 1/R1 + 1/R2.
Power: P = VI = I²R = V²/R, measured in Watts.""",
        },
        {
            "class": 9, "subject": "science",
            "chapter": "Motion",
            "text": """Motion: An object is in motion if its position changes with time relative to a reference point.
Distance: Total path length traveled. Displacement: Shortest distance between initial and final position.
Speed = Distance / Time. Velocity = Displacement / Time (vector quantity).
Acceleration = Change in velocity / Time. Uniform acceleration means constant change in velocity.
Newton's Laws of Motion:
First Law (Inertia): An object at rest stays at rest, and an object in motion stays in motion unless acted upon by an external force.
Second Law: F = ma (Force = mass × acceleration).
Third Law: For every action, there is an equal and opposite reaction.""",
        },
    ]

    for sample in samples:
        key = f"{sample['class']}_{sample['subject']}"
        out_path = os.path.join(DATA_DIR, f"{key}_sample.json")
        # Append to existing or create new
        existing = []
        if os.path.exists(out_path):
            with open(out_path, encoding="utf-8") as f:
                existing = json.load(f)
        existing.append(sample)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"Sample data created in {DATA_DIR}")


if __name__ == "__main__":
    download_from_huggingface()
