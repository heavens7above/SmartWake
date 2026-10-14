"""
PhysioNet Sleep-Accel Adapter Module (Tier C).
Dataset: Motion and Heart Rate from a Wrist-Worn Wearable and Labeled Sleep from Polysomnography (Walch et al. 2019)
PhysioNet DOI: 10.13026/kmwq-bh44
License: Open Data Commons Attribution License v1.0 (ODC-BY 1.0)

Adapts clinical polysomnography ground-truth sleep stages (30-second epochs) and raw triaxial
acceleration into SmartWake's 9-dimensional 5-minute feature vectors without altering model inference logic.
"""

import os
import sys
import math
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PhysioNetAdapter")

BASE_URL = "https://physionet.org/files/sleep-accel/1.0.0/"
SUBJECTS = [
    "1066528",
    "1360686",
    "1449548",
    "1818471",
    "2598705",
    "4426783",
]


def download_file(url: str, dest_path: Path) -> bool:
    if dest_path.exists() and dest_path.stat().st_size > 0:
        logger.info(f"Using cached file: {dest_path}")
        return True

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Downloading {url} -> {dest_path}")
    try:
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
        return True
    except Exception as e:
        logger.error(f"Download error for {url}: {e}")
        dest_path.unlink(missing_ok=True)
        return False


def load_psg_labels(label_file: Path) -> pd.DataFrame:
    """
    PhysioNet PSG labels format:
    timestamp_sec sleep_stage
    Stages: 0 = Wake, 1 = N1, 2 = N2, 3 = N3, 5 = REM, -1 = Unscored
    """
    labels = []
    with open(label_file, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2:
                sec = float(parts[0])
                stage = int(parts[1])
                labels.append({"time_sec": sec, "stage": stage})
    df_labels = pd.DataFrame(labels)
    # Drop unscored epochs
    df_labels = df_labels[df_labels["stage"] >= 0].copy()
    df_labels["is_asleep"] = (df_labels["stage"] > 0).astype(int)
    return df_labels


def process_subject(
    subject_id: str,
    raw_dir: Path,
    window_minutes: int = 5,
    sample_subsample: int = 25,  # Raw is ~50Hz; step by 25 gives ~2Hz (sufficient for 5-min macro window)
) -> Optional[pd.DataFrame]:
    label_url = f"{BASE_URL}labels/{subject_id}_labeled_sleep.txt"
    motion_url = f"{BASE_URL}motion/{subject_id}_acceleration.txt"

    label_path = raw_dir / "labels" / f"{subject_id}_labeled_sleep.txt"
    motion_path = raw_dir / "motion" / f"{subject_id}_acceleration.txt"

    if not download_file(label_url, label_path):
        return None
    if not download_file(motion_url, motion_path):
        return None

    logger.info(f"Processing PSG labels for Subject {subject_id}")
    df_labels = load_psg_labels(label_path)
    if df_labels.empty:
        return None

    min_time = df_labels["time_sec"].min()
    max_time = df_labels["time_sec"].max()

    logger.info(f"Reading motion data for Subject {subject_id} (time range {min_time:.1f} to {max_time:.1f}s)")
    # Stream read acceleration lines to conserve memory
    times = []
    mags = []
    with open(motion_path, "r") as f:
        for line_idx, line in enumerate(f):
            if line_idx % sample_subsample != 0:
                continue
            parts = line.strip().split()
            if len(parts) >= 4:
                t = float(parts[0])
                if t < min_time or t > max_time:
                    continue
                x = float(parts[1]) * 9.80665  # Convert g to m/s^2
                y = float(parts[2]) * 9.80665
                z = float(parts[3]) * 9.80665
                mag = math.sqrt(x**2 + y**2 + z**2)
                times.append(t)
                mags.append(mag)

    if not times:
        logger.warning(f"No motion data overlapping labels for Subject {subject_id}")
        return None

    df_motion = pd.DataFrame({"time_sec": times, "magnitude": mags})

    # Window into 5-minute epochs
    window_sec = window_minutes * 60
    start_sec = math.floor(min_time / window_sec) * window_sec
    end_sec = math.ceil(max_time / window_sec) * window_sec

    feature_rows = []
    nominal_start_datetime = datetime(2026, 1, 15, 23, 0, 0, tzinfo=timezone.utc)

    current_window_start = start_sec
    while current_window_start + window_sec <= end_sec:
        current_window_end = current_window_start + window_sec

        # Slice motion
        m_slice = df_motion[
            (df_motion["time_sec"] >= current_window_start)
            & (df_motion["time_sec"] < current_window_end)
        ]["magnitude"].values

        # Slice labels
        l_slice = df_labels[
            (df_labels["time_sec"] >= current_window_start)
            & (df_labels["time_sec"] < current_window_end)
        ]

        if len(m_slice) >= 10 and not l_slice.empty:
            mean_mag = float(np.mean(m_slice))
            std_mag = float(np.std(m_slice))
            max_mag = float(np.max(m_slice))

            if std_mag > 0:
                mean_centered = m_slice - mean_mag
                zero_crossings = int(np.sum(np.diff(np.sign(mean_centered)) != 0))
                zcr = float(zero_crossings / len(m_slice))
            else:
                zcr = 0.0

            # Stillness: dynamic deviation from gravity (9.81 m/s^2) < 0.05
            dyn_devs = np.abs(m_slice - 9.80665)
            consecutive_still = int(np.sum(dyn_devs < 0.05))

            # Circadian hour sin/cos from nominal time
            elapsed_sec = current_window_end - start_sec
            nominal_dt = nominal_start_datetime + timedelta(seconds=elapsed_sec)
            total_mins = nominal_dt.hour * 60 + nominal_dt.minute
            hour_sin = float(np.sin(2 * np.pi * total_mins / 1440.0))
            hour_cos = float(np.cos(2 * np.pi * total_mins / 1440.0))

            # Ground-truth PSG stage and binary label
            stage_mode = int(l_slice["stage"].mode()[0])
            is_asleep = int(l_slice["is_asleep"].median() > 0.5)

            feature_rows.append({
                "subject_id": f"physionet_{subject_id}",
                "timestamp_sec": current_window_end,
                "nominal_time": nominal_dt.isoformat(),
                "accel_magnitude_mean": mean_mag,
                "accel_magnitude_std": std_mag,
                "accel_magnitude_max": max_mag,
                "zero_crossing_rate": zcr,
                "notification_delta": 0.0,
                "consecutive_still_count": float(consecutive_still),
                "charging": 1.0,
                "hour_sin": hour_sin,
                "hour_cos": hour_cos,
                "stage": stage_mode,  # 0=Wake, 1=N1, 2=N2, 3=N3, 5=REM
                "label": is_asleep,
            })

        current_window_start += window_sec

    df_out = pd.DataFrame(feature_rows)
    logger.info(f"Subject {subject_id}: generated {len(df_out)} 5-minute epochs.")
    return df_out


def build_physionet_dataset(raw_dir: str, output_csv: str) -> pd.DataFrame:
    raw_path = Path(raw_dir)
    raw_path.mkdir(parents=True, exist_ok=True)

    all_dfs = []
    for s in SUBJECTS:
        df_subj = process_subject(s, raw_path)
        if df_subj is not None and not df_subj.empty:
            all_dfs.append(df_subj)

    if not all_dfs:
        raise RuntimeError("Failed to process any PhysioNet subjects.")

    df_total = pd.concat(all_dfs, ignore_index=True)
    out_file = Path(output_csv)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    df_total.to_csv(out_file, index=False)
    logger.info(f"[Tier C] Total PhysioNet dataset assembled: {len(df_total)} rows saved to {output_csv}")
    return df_total


if __name__ == "__main__":
    raw_directory = "research/data/raw/physionet"
    output_filepath = "research/data/processed/tier_c_physionet.csv"
    build_physionet_dataset(raw_directory, output_filepath)
