"""
Tier A Phone Ingestion Module for SmartWake.
Ingests real raw phone telemetry logs from Termux or SQLite/PostgreSQL dumps,
computes the 9-dimensional SmartWake feature vector, and exports to standard tabular format.
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PhoneIngest")


def compute_magnitude(x: float, y: float, z: float) -> float:
    return float(np.sqrt(x**2 + y**2 + z**2))


def cyclical_encode(hour: int, minute: int) -> tuple[float, float]:
    total_minutes = hour * 60 + minute
    sin_val = np.sin(2 * np.pi * total_minutes / 1440.0)
    cos_val = np.cos(2 * np.pi * total_minutes / 1440.0)
    return float(sin_val), float(cos_val)


def extract_features_from_window(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Computes exactly the 9 features defined in SmartWake's server/src/modules/sleep.py:
      1. accel_magnitude_mean
      2. accel_magnitude_std
      3. accel_magnitude_max
      4. zero_crossing_rate
      5. notification_delta
      6. consecutive_still_count
      7. charging
      8. hour_sin
      9. hour_cos
    """
    if not rows:
        raise ValueError("Cannot extract features from empty window.")

    mags = np.array([r["accel_magnitude"] for r in rows], dtype=float)
    accel_magnitude_mean = float(np.mean(mags))
    accel_magnitude_std = float(np.std(mags)) if len(mags) > 1 else 0.0
    accel_magnitude_max = float(np.max(mags))

    if len(mags) > 1 and accel_magnitude_std > 0:
        mean_centered = mags - accel_magnitude_mean
        zero_crossings = int(np.sum(np.diff(np.sign(mean_centered)) != 0))
        zero_crossing_rate = float(zero_crossings / len(mags))
    else:
        zero_crossing_rate = 0.0

    notif_last = rows[-1].get("notification_count", 0)
    notif_first = rows[0].get("notification_count", 0)
    notification_delta = float(notif_last - notif_first)

    # In repo's sleep.py, still threshold is 0.05
    consecutive_still_count = 0
    for r in reversed(rows):
        if r["accel_magnitude"] < 0.05:
            consecutive_still_count += 1
        else:
            break

    charging = 1.0 if rows[-1].get("charging", False) else 0.0

    last_dt = rows[-1]["timestamp"]
    if isinstance(last_dt, str):
        last_dt = datetime.fromisoformat(last_dt.replace("Z", "+00:00"))

    hour_sin, hour_cos = cyclical_encode(last_dt.hour, last_dt.minute)

    return {
        "accel_magnitude_mean": accel_magnitude_mean,
        "accel_magnitude_std": accel_magnitude_std,
        "accel_magnitude_max": accel_magnitude_max,
        "zero_crossing_rate": zero_crossing_rate,
        "notification_delta": notification_delta,
        "consecutive_still_count": float(consecutive_still_count),
        "charging": charging,
        "hour_sin": hour_sin,
        "hour_cos": hour_cos,
    }


def ingest_phone_logs(input_dir: str, output_path: str, window_size: int = 6) -> Optional[pd.DataFrame]:
    """
    Scans input_dir for phone log files (.json, .jsonl, .csv).
    Returns processed DataFrame or None if directory contains no real recordings.
    """
    path = Path(input_dir)
    if not path.exists():
        logger.warning(f"Input directory does not exist: {input_dir}")
        return None

    files = list(path.glob("*.json")) + list(path.glob("*.jsonl")) + list(path.glob("*.csv"))
    if not files:
        logger.info(f"No real phone log files found in {input_dir}.")
        return None

    records = []
    for file in sorted(files):
        logger.info(f"Reading phone telemetry from {file.name}")
        if file.suffix in [".json", ".jsonl"]:
            with open(file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line.strip()))
        elif file.suffix == ".csv":
            df_temp = pd.read_csv(file)
            records.extend(df_temp.to_dict(orient="records"))

    if not records:
        return None

    df_raw = pd.DataFrame(records)
    # Ensure accel_magnitude
    if "accel_magnitude" not in df_raw.columns:
        df_raw["accel_magnitude"] = [
            compute_magnitude(r["accel_x"], r["accel_y"], r["accel_z"])
            for _, r in df_raw.iterrows()
        ]

    df_raw["timestamp"] = pd.to_datetime(df_raw["timestamp"])
    df_raw = df_raw.sort_values(by=["device_id", "timestamp"])

    feature_rows = []
    for device_id, group in df_raw.groupby("device_id"):
        group_records = group.to_dict(orient="records")
        for i in range(len(group_records)):
            # Window of up to window_size preceding rows
            start_idx = max(0, i - window_size + 1)
            window = group_records[start_idx : i + 1]
            if len(window) < 2:
                continue
            feats = extract_features_from_window(window)
            feats["device_id"] = device_id
            feats["timestamp"] = group_records[i]["timestamp"]
            if "label" in group_records[i]:
                feats["label"] = group_records[i]["label"]
            feature_rows.append(feats)

    if not feature_rows:
        return None

    df_out = pd.DataFrame(feature_rows)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_out.to_csv(output_path, index=False)
    logger.info(f"Successfully processed {len(df_out)} feature rows to {output_path}")
    return df_out


if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "research/data/raw/phone_recordings"
    out_file = sys.argv[2] if len(sys.argv) > 2 else "research/data/processed/tier_a_phone.csv"
    res = ingest_phone_logs(data_dir, out_file)
    if res is None:
        print("[NOTICE] No Tier A real phone recordings present in repo. Protocol active.")
