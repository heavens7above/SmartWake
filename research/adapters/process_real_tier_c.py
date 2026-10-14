"""
Process real PhysioNet sleep-accel subjects into Tier C features and evaluate sleep-onset error.
"""

import math
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, matthews_corrcoef

RAW_DIR = Path("research/data/raw/physionet")
PROCESSED_FILE = Path("research/data/processed/tier_c_physionet.csv")

SUBJECTS = ["1066528", "1360686", "1449548", "1818471"]

def process_all_tier_c():
    all_rows = []

    for s_id in SUBJECTS:
        label_file = RAW_DIR / "labels" / f"{s_id}_labeled_sleep.txt"
        motion_file = RAW_DIR / "motion" / f"{s_id}_sleep_motion.txt"

        if not label_file.exists() or not motion_file.exists():
            print(f"Skipping {s_id}: files missing")
            continue

        # Load labels
        labels = []
        with open(label_file) as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 2:
                    t = float(parts[0])
                    st = int(parts[1])
                    if st >= 0:
                        labels.append((t, st))
        df_l = pd.DataFrame(labels, columns=["time_sec", "stage"])
        df_l["is_asleep"] = (df_l["stage"] > 0).astype(int)

        # Load motion
        motion = []
        with open(motion_file) as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 4:
                    try:
                        t = float(parts[0])
                        x = float(parts[1]) * 9.80665
                        y = float(parts[2]) * 9.80665
                        z = float(parts[3]) * 9.80665
                        mag = math.sqrt(x**2 + y**2 + z**2)
                        motion.append((t, mag))
                    except ValueError:
                        pass
        df_m = pd.DataFrame(motion, columns=["time_sec", "magnitude"])
        df_m = df_m.sort_values("time_sec").reset_index(drop=True)

        if len(df_m) < 100 or len(df_l) < 5:
            continue

        min_t = max(df_l["time_sec"].min(), df_m["time_sec"].min())
        max_t = min(df_l["time_sec"].max(), df_m["time_sec"].max())

        print(f"Subject {s_id}: Overlap from {min_t:.1f}s to {max_t:.1f}s ({(max_t-min_t)/60:.1f} min)")

        # Aggregate into 5-minute epochs (300 sec)
        epoch_len = 300
        cur_t = math.floor(min_t / epoch_len) * epoch_len

        while cur_t + epoch_len <= max_t:
            t_start = cur_t
            t_end = cur_t + epoch_len

            m_sub = df_m[(df_m["time_sec"] >= t_start) & (df_m["time_sec"] < t_end)]["magnitude"].values
            l_sub = df_l[(df_l["time_sec"] >= t_start) & (df_l["time_sec"] < t_end)]

            if len(m_sub) >= 5 and len(l_sub) >= 1:
                mean_mag = float(np.mean(m_sub))
                std_mag = float(np.std(m_sub))
                max_mag = float(np.max(m_sub))

                centered = m_sub - mean_mag
                zcr = float(np.sum(np.diff(np.sign(centered)) != 0) / len(m_sub)) if len(m_sub) > 1 else 0.0

                diffs = np.abs(m_sub - 9.81)
                consec_still = float(np.sum(diffs < 0.20))

                # Nominal bedtime starting at 23:00 UTC
                nominal_dt = datetime(2026, 1, 15, 23, 0, 0, tzinfo=timezone.utc) + pd.Timedelta(seconds=t_start)
                hour_float = nominal_dt.hour + nominal_dt.minute / 60.0
                h_sin = float(math.sin(2.0 * math.pi * hour_float / 24.0))
                h_cos = float(math.cos(2.0 * math.pi * hour_float / 24.0))

                maj_stage = int(l_sub["stage"].mode()[0])
                label = 1 if maj_stage > 0 else 0

                all_rows.append({
                    "subject_id": f"physionet_{s_id}",
                    "timestamp_sec": t_start,
                    "accel_magnitude_mean": mean_mag,
                    "accel_magnitude_std": std_mag,
                    "accel_magnitude_max": max_mag,
                    "zero_crossing_rate": zcr,
                    "notification_delta": 0.0,
                    "consecutive_still_count": consec_still,
                    "charging": 1.0,
                    "hour_sin": h_sin,
                    "hour_cos": h_cos,
                    "stage": maj_stage,
                    "label": label,
                })

            cur_t += epoch_len

    df_out = pd.DataFrame(all_rows)
    df_out.to_csv(PROCESSED_FILE, index=False)
    print(f"\nGenerated Tier C Clinical Dataset: {len(df_out)} 5-minute epochs across {df_out['subject_id'].nunique()} subjects!")
    print(df_out["label"].value_counts(normalize=True))
    print(df_out.groupby("stage")["accel_magnitude_std"].agg(["mean", "count"]))
    return df_out

if __name__ == "__main__":
    process_all_tier_c()
