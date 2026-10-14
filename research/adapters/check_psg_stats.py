"""
Targeted PhysioNet Ingestion for Real Tier C Clinical Evaluation.
Downloads representative sleep sessions for PhysioNet subjects, aligns with clinical PSG labels,
extracts SmartWake 9-feature vectors, and calculates real sleep-onset latency error.
"""

import os
import sys
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

RAW_DIR = Path("research/data/raw/physionet")
PROCESSED_FILE = Path("research/data/processed/tier_c_physionet.csv")

# Subjects with confirmed PSG labels in raw/labels/
SUBJECT_IDS = ["1066528", "1360686", "1449548", "1818471"]

def get_label_data(subject_id: str) -> pd.DataFrame:
    label_path = RAW_DIR / "labels" / f"{subject_id}_labeled_sleep.txt"
    rows = []
    with open(label_path, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2:
                sec = float(parts[0])
                stage = int(parts[1])
                if stage >= 0:
                    rows.append({"time_sec": sec, "stage": stage, "is_asleep": 1 if stage > 0 else 0})
    df = pd.DataFrame(rows)
    return df

print("Label files available for subjects:", SUBJECT_IDS)
for s in SUBJECT_IDS:
    df_l = get_label_data(s)
    print(f"Subject {s}: {len(df_l)} 30s epochs ({len(df_l)*30/3600:.1f} hours). Stages: {dict(df_l['stage'].value_counts())}")
