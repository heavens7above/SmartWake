"""
Targeted Clinical PhysioNet Motion Ingestion.
Downloads exact nocturnal sleep interval acceleration ranges for 4 PSG subjects,
converts to SmartWake 9-feature vectors, and produces research/data/processed/tier_c_physionet.csv.
"""

import os
import sys
import math
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

SUBJECTS = ["1066528", "1360686", "1449548", "1818471"]
RAW_DIR = Path("research/data/raw/physionet")
PROCESSED_FILE = Path("research/data/processed/tier_c_physionet.csv")

RAW_DIR.joinpath("motion").mkdir(parents=True, exist_ok=True)
RAW_DIR.joinpath("labels").mkdir(parents=True, exist_ok=True)


def download_subject_slice(subject_id: str, start_byte: int = 4000000, end_byte: int = 6000000) -> Path:
    out_file = RAW_DIR / "motion" / f"{subject_id}_sleep_motion.txt"
    if out_file.exists() and out_file.stat().st_size > 1000000:
        print(f"Subject {subject_id}: using cached motion slice ({out_file.stat().st_size / 1e6:.1f} MB)")
        return out_file

    url = f"https://physionet.org/files/sleep-accel/1.0.0/motion/{subject_id}_acceleration.txt"
    print(f"Subject {subject_id}: downloading sleep range {start_byte}-{end_byte} ({((end_byte-start_byte)/1e6):.1f} MB)...")
    cmd = ["curl", "-sL", "-r", f"{start_byte}-{end_byte}", url, "-o", str(out_file)]
    subprocess.run(cmd, check=True)
    print(f"Subject {subject_id}: download complete ({out_file.stat().st_size / 1e6:.1f} MB)")
    return out_file


def process_subject(subject_id: str, motion_path: Path, window_minutes: int = 5) -> pd.DataFrame:
    label_path = RAW_DIR / "labels" / f"{subject_id}_labeled_sleep.txt"
    labels = []
    with open(label_path, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2:
                sec = float(parts[0])
                stage = int(parts[1])
                if stage >= 0:
                    labels.append({"time_sec": sec, "stage": stage, "is_asleep": 1 if stage > 0 else 0})
    df_labels = pd.DataFrame(labels)

    times = []
    mags = []
    sample_step = 10  # Subsample 50Hz to 5Hz
    with open(motion_path, "r") as f:
        for idx, line in enumerate(f):
            if idx % sample_step != 0:
                continue
            parts = line.strip().split()
            if len(parts) >= 4:
                try:
                    t = float(parts[0])
                    x = float(parts[1]) * 9.80665
                    y = float(parts[2]) * 9.80665
                    z = float(parts[3]) * 9.80665
                    mag = math.sqrt(x**2 + y**2 + z**2)
                    times.append(t)
                    mags.append(mag)
                except ValueError:
                    continue

    df_motion = pd.DataFrame({"time_sec": times, "magnitude": mags})
    min_time = max(0.0, df_motion["time_sec"].min())
    max_time = min(df_labels["time_sec"].max(), df_motion["time_sec"].max())

    window_sec = window_minutes * 60
    start_sec = math.floor(min_time / window_sec) * window_sec
    end_sec = math.ceil(max_time / window_sec) * window_sec

    nominal_start = datetime(2026, 1, 15, 23, 0, 0, tzinfo=timezone.utc)
    epochs = []

    cur = start_sec
    while cur + window_sec <= end_sec:
        m_vals = df_motion[(df_motion["time_sec"] >= cur) & (df_motion["time_sec"] < cur + window_sec)]["magnitude"].values
        l_sub = df_labels[(df_labels["time_sec"] >= cur) & (df_labels["time_sec"] < cur + window_sec)]

        if len(m_vals) >= 10 and not l_sub.empty:
            mean_m = float(np.mean(m_vals))
            std_m = float(np.std(m_vals))
            max_m = float(np.max(m_vals))

            if std_m > 0:
                mean_centered = m_vals - mean_m
                zcr = float(np.sum(np.diff(np.sign(mean_centered)) != 0) / len(m_vals))
            else:
                zcr = 0.0

            dyn = np.abs(m_vals - 9.80665)
            consecutive_still = int(np.sum(dyn < 0.05))

            elapsed = cur + window_sec - start_sec
            dt = nominal_start + timedelta(seconds=elapsed)
            mins = dt.hour * 60 + dt.minute
            hour_sin = float(np.sin(2 * np.pi * mins / 1440.0))
            hour_cos = float(np.cos(2 * np.pi * mins / 1440.0))

            stage = int(l_sub["stage"].mode()[0])
            label = int(l_sub["is_asleep"].median() > 0.5)

            epochs.append({
                "subject_id": f"physionet_{subject_id}",
                "timestamp_sec": cur + window_sec,
                "nominal_time": dt.isoformat(),
                "accel_magnitude_mean": mean_m,
                "accel_magnitude_std": std_m,
                "accel_magnitude_max": max_m,
                "zero_crossing_rate": zcr,
                "notification_delta": 0.0,
                "consecutive_still_count": float(consecutive_still),
                "charging": 1.0,
                "hour_sin": hour_sin,
                "hour_cos": hour_cos,
                "stage": stage,
                "label": label,
            })
        cur += window_sec

    df_out = pd.DataFrame(epochs)
    print(f"Subject {subject_id}: extracted {len(df_out)} 5-minute epochs (Sleep ratio: {df_out['label'].mean():.2f}).")
    return df_out


def main():
    dfs = []
    for s in SUBJECTS:
        try:
            m_path = download_subject_slice(s)
            df_s = process_subject(s, m_path)
            if not df_s.empty:
                dfs.append(df_s)
        except Exception as e:
            print(f"Error on {s}: {e}")

    if not dfs:
        raise RuntimeError("No subjects processed.")

    df_total = pd.concat(dfs, ignore_index=True)
    PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)
    df_total.to_csv(PROCESSED_FILE, index=False)
    print(f"\n[Tier C] SUCCESS: {len(df_total)} total epochs across {len(dfs)} subjects saved to {PROCESSED_FILE}")


if __name__ == "__main__":
    main()
