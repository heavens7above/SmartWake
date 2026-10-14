"""
Physiologically-Grounded Synthetic Telemetry Generator (Tier B).
Simulates nocturnal smartphone accelerometer and state telemetry based on peer-reviewed
sleep architecture parameters (Carskadon & Dement 2011; Basner et al. 2008; Cole et al. 1992).

STRICT COMPLIANCE NOTICE:
All generated outputs are explicitly labeled with 'synthetic_' and restricted solely to
pipeline testing, noise sensitivity sweeps, and demonstrating evaluation inflation.
They are NEVER presented as evidence of real-world clinical performance.
"""

import os
import sys
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import numpy as np
import pandas as pd

# Fixed seed per project specification
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)


class SleepPhysiologySimulator:
    """
    Physiological parameters cited:
    - Carskadon & Dement (2011): 90-110 min ultradian cycle period; N1=5%, N2=50%, N3=20%, REM=25%.
    - Feinberg & Floyd (1979): N3 dominates early nocturnal cycles; REM dominates terminal cycles.
    - Basner et al. (2008) & Cole et al. (1992): Stage-dependent movement probabilities.
    - Borbély (1982): Two-process model of sleep regulation (Process C circadian, Process S homeostatic).
    """

    STAGE_WAKE = 0
    STAGE_N1 = 1
    STAGE_N2 = 2
    STAGE_N3 = 3
    STAGE_REM = 5

    STAGE_MOVEMENT_PROB = {
        STAGE_WAKE: 0.70,  # Frequent gross body movements
        STAGE_N1: 0.25,    # Hypnic jerks and transitional repositioning
        STAGE_N2: 0.08,    # Occasional postural shifts
        STAGE_N3: 0.02,    # Deep slow-wave sleep; profound motor quiescence
        STAGE_REM: 0.05,   # Postural muscle atonia with sporadic distal twitches
    }

    STAGE_ACCEL_MAGNITUDE_PARAMS = {
        STAGE_WAKE: (0.80, 0.50),   # (mean m/s^2, std m/s^2) dynamic movement
        STAGE_N1:   (0.25, 0.15),
        STAGE_N2:   (0.10, 0.06),
        STAGE_N3:   (0.02, 0.01),
        STAGE_REM:  (0.04, 0.03),
    }

    def __init__(self, sample_interval_minutes: int = 5, noise_std: float = 0.01):
        self.interval = sample_interval_minutes
        self.noise_std = noise_std

    def generate_night(
        self,
        subject_id: str,
        bedtime: datetime,
        sleep_duration_hours: float = 7.5,
        sleep_latency_minutes: float = 20.0,
    ) -> List[Dict]:
        total_minutes = int(sleep_duration_hours * 60)
        num_epochs = total_minutes // self.interval
        cycle_period_minutes = np.random.normal(90.0, 10.0)

        records = []
        cumulative_notifs = np.random.randint(2, 10)

        for epoch in range(num_epochs):
            t_min = epoch * self.interval
            current_time = bedtime + timedelta(minutes=t_min)

            # Determine physiological stage
            if t_min < sleep_latency_minutes:
                stage = self.STAGE_WAKE
                is_asleep = 0
            else:
                sleep_min = t_min - sleep_latency_minutes
                cycle_phase = (sleep_min % cycle_period_minutes) / cycle_period_minutes
                cycle_num = int(sleep_min // cycle_period_minutes)

                # N3 dominates cycles 0-2; REM dominates cycles 3+
                if cycle_num < 2:
                    if cycle_phase < 0.10:
                        stage = self.STAGE_N1
                    elif cycle_phase < 0.45:
                        stage = self.STAGE_N2
                    elif cycle_phase < 0.85:
                        stage = self.STAGE_N3
                    else:
                        stage = self.STAGE_REM
                else:
                    if cycle_phase < 0.10:
                        stage = self.STAGE_N1
                    elif cycle_phase < 0.55:
                        stage = self.STAGE_N2
                    elif cycle_phase < 0.65:
                        stage = self.STAGE_N3
                    else:
                        stage = self.STAGE_REM
                is_asleep = 1

            # Brief spontaneous nocturnal awakenings (Cole-Kripke micro-arousals)
            if is_asleep and np.random.rand() < 0.03:
                stage = self.STAGE_WAKE
                is_asleep = 0

            # Movement kinematics
            move_prob = self.STAGE_MOVEMENT_PROB[stage]
            has_movement = np.random.rand() < move_prob

            mean_dyn, std_dyn = self.STAGE_ACCEL_MAGNITUDE_PARAMS[stage]
            if has_movement:
                dyn_mag = float(np.abs(np.random.normal(mean_dyn, std_dyn)))
            else:
                dyn_mag = float(np.abs(np.random.normal(0.01, 0.005)))

            # Phone flat on bed: gravity along z-axis (~9.81 m/s^2) + noise + mattress dampening
            # Dynamic movement distributes randomly across axes
            theta = np.random.uniform(0, 2 * np.pi)
            phi = np.random.uniform(0, np.pi)
            acc_x = dyn_mag * np.sin(phi) * np.cos(theta) + np.random.normal(0, self.noise_std)
            acc_y = dyn_mag * np.sin(phi) * np.sin(theta) + np.random.normal(0, self.noise_std)
            acc_z = 9.81 + dyn_mag * np.cos(phi) + np.random.normal(0, self.noise_std)

            total_mag = float(np.sqrt(acc_x**2 + acc_y**2 + acc_z**2))

            # Device state: charging overnight, occasional night notification
            charging = True
            battery_level = min(100, 75 + int(epoch * 0.5))
            if np.random.rand() < 0.05:
                cumulative_notifs += 1

            records.append({
                "device_id": subject_id,
                "timestamp": current_time.isoformat(),
                "charging": charging,
                "battery_level": battery_level,
                "accel_x": float(acc_x),
                "accel_y": float(acc_y),
                "accel_z": float(acc_z),
                "accel_magnitude": total_mag,
                "notification_count": cumulative_notifs,
                "hour": current_time.hour,
                "minute": current_time.minute,
                "stage": stage,
                "is_asleep": is_asleep,
            })

        return records


def build_synthetic_dataset(
    output_dir: str,
    num_subjects: int = 5,
    nights_per_subject: int = 14,
    interval_min: int = 5,
    noise_std: float = 0.01,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    simulator = SleepPhysiologySimulator(sample_interval_minutes=interval_min, noise_std=noise_std)
    all_raw_records = []

    base_date = datetime(2026, 1, 10, 23, 0, 0, tzinfo=timezone.utc)

    for s_idx in range(num_subjects):
        subject_id = f"synthetic_subject_{s_idx+1:02d}"
        for n_idx in range(nights_per_subject):
            night_date = base_date + timedelta(days=n_idx, minutes=int(np.random.normal(0, 20)))
            night_records = simulator.generate_night(
                subject_id=subject_id,
                bedtime=night_date,
                sleep_duration_hours=np.random.normal(7.8, 0.6),
                sleep_latency_minutes=np.random.normal(18.0, 5.0),
            )
            all_raw_records.extend(night_records)

    df_raw = pd.DataFrame(all_raw_records)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    raw_file = out_path / "synthetic_raw_telemetry.csv"
    df_raw.to_csv(raw_file, index=False)

    # Now compute 9-feature representations across 6-epoch rolling windows
    feature_rows = []
    window_size = 6

    for subject_id, group in df_raw.groupby("device_id"):
        group_records = group.to_dict(orient="records")
        for i in range(len(group_records)):
            start_idx = max(0, i - window_size + 1)
            window = group_records[start_idx : i + 1]
            if len(window) < 2:
                continue

            # Standard 9 features
            mags = np.array([r["accel_magnitude"] for r in window], dtype=float)
            accel_mean = float(np.mean(mags))
            accel_std = float(np.std(mags))
            accel_max = float(np.max(mags))

            if len(mags) > 1 and accel_std > 0:
                mean_centered = mags - accel_mean
                zero_crossings = int(np.sum(np.diff(np.sign(mean_centered)) != 0))
                zcr = float(zero_crossings / len(mags))
            else:
                zcr = 0.0

            notif_delta = float(window[-1]["notification_count"] - window[0]["notification_count"])

            consecutive_still = 0
            for r in reversed(window):
                # Subtract gravity baseline ~9.81 to assess motion still
                dyn = abs(r["accel_magnitude"] - 9.81)
                if dyn < 0.05:
                    consecutive_still += 1
                else:
                    break

            charging = 1.0 if window[-1]["charging"] else 0.0
            dt = datetime.fromisoformat(window[-1]["timestamp"])
            total_mins = dt.hour * 60 + dt.minute
            hour_sin = float(np.sin(2 * np.pi * total_mins / 1440.0))
            hour_cos = float(np.cos(2 * np.pi * total_mins / 1440.0))

            feature_rows.append({
                "device_id": subject_id,
                "timestamp": window[-1]["timestamp"],
                "accel_magnitude_mean": accel_mean,
                "accel_magnitude_std": accel_std,
                "accel_magnitude_max": accel_max,
                "zero_crossing_rate": zcr,
                "notification_delta": notif_delta,
                "consecutive_still_count": float(consecutive_still),
                "charging": charging,
                "hour_sin": hour_sin,
                "hour_cos": hour_cos,
                "stage": window[-1]["stage"],
                "label": window[-1]["is_asleep"],
            })

    df_feats = pd.DataFrame(feature_rows)
    feat_file = out_path / "synthetic_features.csv"
    df_feats.to_csv(feat_file, index=False)

    return df_raw, df_feats


if __name__ == "__main__":
    out_dir = "research/data/processed/synthetic"
    df_r, df_f = build_synthetic_dataset(out_dir, num_subjects=5, nights_per_subject=14)
    print(f"[Tier B] Generated {len(df_r)} raw synthetic rows and {len(df_f)} feature vectors.")
