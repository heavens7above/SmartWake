"""
High-Speed Parallel PhysioNet Ingestion Engine.
Downloads exact nocturnal PSG sleep intervals and acceleration ranges,
avoiding unnecessary post-sleep afternoon data, and computes SmartWake 9-feature vectors.
"""

import os
import sys
import math
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("FastPhysioNet")

BASE_URL = "https://physionet.org/files/sleep-accel/1.0.0/"
SUBJECTS = [
    "1066528",
    "1360686",
    "1449548",
    "1818471",
    "2598705",
    "4426783",
]


def load_or_download_label(subject_id: str, raw_dir: Path) -> pd.DataFrame:
    label_path = raw_dir / "labels" / f"{subject_id}_labeled_sleep.txt"
    label_path.parent.mkdir(parents=True, exist_ok=True)
    if not label_path.exists() or label_path.stat().st_size == 0:
        url = f"{BASE_URL}labels/{subject_id}_labeled_sleep.txt"
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        label_path.write_text(r.text, encoding="utf-8")

    labels = []
    with open(label_path, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2:
                sec = float(parts[0])
                stage = int(parts[1])
                labels.append({"time_sec": sec, "stage": stage})
    df_labels = pd.DataFrame(labels)
    df_labels = df_labels[df_labels["stage"] >= 0].copy()
    df_labels["is_asleep"] = (df_labels["stage"] > 0).astype(int)
    return df_labels


def download_motion_chunk(subject_id: str, raw_dir: Path, byte_limit: int = 16 * 1024 * 1024) -> Path:
    motion_path = raw_dir / "motion" / f"{subject_id}_acceleration.txt"
    motion_path.parent.mkdir(parents=True, exist_ok=True)
    if motion_path.exists() and motion_path.stat().st_size >= byte_limit:
        logger.info(f"Using cached motion for {subject_id} ({motion_path.stat().st_size / 1e6:.1f} MB)")
        return motion_path

    url = f"{BASE_URL}motion/{subject_id}_acceleration.txt"
    headers = {"Range": f"bytes=0-{byte_limit}"}
    logger.info(f"Downloading first {byte_limit / 1e6:.1f} MB for subject {subject_id}...")
    r = requests.get(url, headers=headers, stream=True, timeout=60)
    r.raise_for_status()
    with open(motion_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=512 * 1024):
            if chunk:
                f.write(chunk)
    logger.info(f"Saved motion chunk for {subject_id} ({motion_path.stat().st_size / 1e6:.1f} MB)")
    return motion_path


def process_subject_fast(subject_id: str, raw_dir: Path, window_minutes: int = 5) -> Optional[pd.DataFrame]:
    try:
        df_labels = load_or_download_label(subject_id, raw_dir)
        if df_labels.empty:
            return None

        min_psg_time = df_labels["time_sec"].min()
        max_psg_time = df_labels["time_sec"].max()

        motion_file = download_motion_chunk(subject_id, raw_dir, byte_limit=16 * 1024 * 1024)

        times = []
        mags = []
        sample_step = 20  # Subsample from ~50Hz to ~2.5Hz

        with open(motion_file, "r") as f:
            for idx, line in enumerate(f):
                if idx % sample_step != 0:
                    continue
                parts = line.strip().split()
                if len(parts) >= 4:
                    try:
                        t = float(parts[0])
                        if t < min_psg_time - 300 or t > max_psg_time + 300:
                            continue
                        x = float(parts[1]) * 9.80665
                        y = float(parts[2]) * 9.80665
                        z = float(parts[3]) * 9.80665
                        mag = math.sqrt(x**2 + y**2 + z**2)
                        times.append(t)
                        mags.append(mag)
                    except ValueError:
                        continue

        if len(times) < 50:
            logger.warning(f"Insufficient motion data for {subject_id}")
            return None

        df_motion = pd.DataFrame({"time_sec": times, "magnitude": mags})
        window_sec = window_minutes * 60
        start_sec = math.floor(min_psg_time / window_sec) * window_sec
        end_sec = math.ceil(max_psg_time / window_sec) * window_sec

        nominal_start_datetime = datetime(2026, 1, 15, 23, 0, 0, tzinfo=timezone.utc)
        feature_rows = []

        cur_start = start_sec
        while cur_start + window_sec <= end_sec:
            cur_end = cur_start + window_sec
            m_slice = df_motion[
                (df_motion["time_sec"] >= cur_start) & (df_motion["time_sec"] < cur_end)
            ]["magnitude"].values

            l_slice = df_labels[
                (df_labels["time_sec"] >= cur_start) & (df_labels["time_sec"] < cur_end)
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

                dyn_devs = np.abs(m_slice - 9.80665)
                consecutive_still = int(np.sum(dyn_devs < 0.05))

                elapsed_sec = cur_end - start_sec
                nominal_dt = nominal_start_datetime + timedelta(seconds=elapsed_sec)
                total_mins = nominal_dt.hour * 60 + nominal_dt.minute
                hour_sin = float(np.sin(2 * np.pi * total_mins / 1440.0))
                hour_cos = float(np.cos(2 * np.pi * total_mins / 1440.0))

                stage_mode = int(l_slice["stage"].mode()[0])
                is_asleep = int(l_slice["is_asleep"].median() > 0.5)

                feature_rows.append({
                    "subject_id": f"physionet_{subject_id}",
                    "timestamp_sec": cur_end,
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
                    "stage": stage_mode,
                    "label": is_asleep,
                })

            cur_start += window_sec

        logger.info(f"Subject {subject_id}: Successfully processed {len(feature_rows)} 5-min epochs.")
        return pd.DataFrame(feature_rows)

    except Exception as e:
        logger.exception(f"Error processing {subject_id}: {e}")
        return None


def main():
    raw_dir = Path("research/data/raw/physionet")
    out_file = Path("research/data/processed/tier_c_physionet.csv")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    all_dfs = []
    # Process sequentially or in 2 workers
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(process_subject_fast, s, raw_dir) for s in SUBJECTS]
        for f in futures:
            res = f.result()
            if res is not None and not res.empty:
                all_dfs.append(res)

    if not all_dfs:
        raise RuntimeError("No subjects processed successfully.")

    df_total = pd.concat(all_dfs, ignore_index=True)
    df_total.to_csv(out_file, index=False)
    logger.info(f"[Tier C] DONE: Assembled {len(df_total)} epochs across {len(all_dfs)} subjects -> {out_file}")


if __name__ == "__main__":
    main()
