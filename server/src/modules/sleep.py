import logging
import os
import shutil
import warnings
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
from fastapi import APIRouter, File, HTTPException, UploadFile

from src.modules.alarms import get_alarm, schedule_alarm
from src.modules.shared import (
    LogPayload,
    compute_magnitude,
    cyclical_encode,
    get_db,
    normalize_datetime,
)

router = APIRouter()

# Canonical model location — always written/read here
SERVER_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = SRC_ROOT / "model"
MODEL_FILE = MODEL_DIR / "sleep_model.pkl"
EXPECTED_FEATURE_COUNT = 9

# ======================== ML Inference & Features ========================
model = None
model_load_attempted = False
_model_source_path: str | None = None


class ModelUnavailableError(RuntimeError):
    pass


def _resolve_model_path(raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return SERVER_ROOT / candidate


def _display_model_path(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.relative_to(SERVER_ROOT))
    except ValueError:
        return str(path)


def _validate_model_instance(candidate):
    if not hasattr(candidate, "predict_proba"):
        raise ValueError("Model must expose predict_proba().")

    feature_count = getattr(candidate, "n_features_in_", None)
    if feature_count is not None and feature_count != EXPECTED_FEATURE_COUNT:
        raise ValueError(
            f"Model expects {feature_count} features; SmartWake sends {EXPECTED_FEATURE_COUNT}."
        )

    return candidate


def _candidate_model_paths():
    configured = os.getenv("MODEL_PATH")
    candidates = []
    if configured:
        candidates.append(_resolve_model_path(configured))

    candidates.extend(
        [
            MODEL_FILE,
            SRC_ROOT / "ml" / "sleep_model.pkl",
            SRC_ROOT / "sleep_model.pkl",
        ]
    )

    seen, unique = set(), []
    for candidate in candidates:
        key = str(candidate.resolve()) if candidate.exists() else str(candidate)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def get_model(force_reload: bool = False):
    global model, model_load_attempted, _model_source_path
    if model_load_attempted and not force_reload:
        return model

    model_load_attempted = True
    model = None
    _model_source_path = None

    for model_path in _candidate_model_paths():
        if not model_path.exists():
            continue
        try:
            model = _validate_model_instance(joblib.load(model_path))
            _model_source_path = str(model_path)
            logging.info("Loaded sleep model from %s", model_path)
            break
        except Exception:
            logging.exception("Failed to load sleep model from %s", model_path)

    if model is None:
        logging.warning("Sleep model not found or invalid.")
    return model


def predict(feature_vector: np.ndarray) -> float:
    current_model = get_model()
    if current_model is None:
        raise ModelUnavailableError(
            f"Sleep model is unavailable. Upload a valid model to {_display_model_path(MODEL_FILE)}."
        )

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            probs = current_model.predict_proba(feature_vector)
    except Exception as exc:
        raise ModelUnavailableError(f"Sleep model inference failed: {exc}") from exc

    classes = list(getattr(current_model, "classes_", []))
    positive_index = (
        classes.index(1) if 1 in classes else (1 if probs.shape[1] > 1 else None)
    )
    if positive_index is None:
        raise ModelUnavailableError(
            "Sleep model does not expose a positive sleep class."
        )

    probability = float(probs[0][positive_index])
    if not 0.0 <= probability <= 1.0:
        raise ModelUnavailableError(
            "Sleep model returned an invalid probability outside [0, 1]."
        )
    return probability


def build_feature_vector(rows: list) -> np.ndarray:
    if not rows:
        return np.zeros((1, EXPECTED_FEATURE_COUNT))

    mags = np.array([r["accel_magnitude"] for r in rows], dtype=float)
    accel_magnitude_mean = np.mean(mags)
    accel_magnitude_std = np.std(mags)
    accel_magnitude_max = np.max(mags)

    if len(mags) > 1 and accel_magnitude_std > 0:
        mean_centered = mags - accel_magnitude_mean
        zero_crossings = np.sum(np.diff(np.sign(mean_centered)) != 0)
        zero_crossing_rate = zero_crossings / len(mags)
    else:
        zero_crossing_rate = 0.0

    notification_delta = rows[-1]["notification_count"] - rows[0]["notification_count"]
    consecutive_still_count = 0
    for row in reversed(rows):
        if row["accel_magnitude"] < 0.05:
            consecutive_still_count += 1
        else:
            break

    charging = 1 if rows[-1]["charging"] else 0
    hour_sin, hour_cos = cyclical_encode(rows[-1]["hour"], rows[-1]["minute"])

    features = np.array(
        [
            accel_magnitude_mean,
            accel_magnitude_std,
            accel_magnitude_max,
            zero_crossing_rate,
            notification_delta,
            consecutive_still_count,
            charging,
            hour_sin,
            hour_cos,
        ],
        dtype=float,
    )
    if not np.isfinite(features).all():
        raise ValueError("Telemetry feature vector contains non-finite values.")
    return np.array([features])


# ======================== Onset State Machine ========================
onset_state = {}
THRESHOLD = 0.75


def _should_reset_confirmed_state(device_id: str, timestamp: str, state: dict) -> bool:
    onset_time = state.get("onset_time")
    if not onset_time:
        return True

    try:
        current_dt = normalize_datetime(datetime.fromisoformat(timestamp))
        onset_dt = normalize_datetime(datetime.fromisoformat(onset_time))
    except (TypeError, ValueError):
        return True

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COALESCE(alarm_time, wake_deadline) AS reset_time
            FROM sleep_sessions
            WHERE device_id = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (device_id,),
        )
        session_row = cursor.fetchone()

    try:
        if session_row and session_row["reset_time"]:
            reset_dt = normalize_datetime(
                datetime.fromisoformat(session_row["reset_time"])
            )
            return current_dt >= reset_dt
        return current_dt - onset_dt >= timedelta(hours=16)
    except (TypeError, ValueError):
        return True


def process_log(device_id: str, timestamp: str, sleep_prob: float):
    if device_id not in onset_state:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT onset_time
                FROM sleep_sessions
                WHERE device_id = %s AND alarm_fired = FALSE AND onset_time IS NOT NULL
                ORDER BY id DESC
                LIMIT 1
                """,
                (device_id,),
            )
            row = cursor.fetchone()
            if row:
                onset_state[device_id] = {
                    "consecutive": 2,
                    "confirmed": True,
                    "onset_time": row["onset_time"],
                }
            else:
                onset_state[device_id] = {
                    "consecutive": 0,
                    "confirmed": False,
                    "onset_time": None,
                }

    state = onset_state[device_id]

    if state["confirmed"] and _should_reset_confirmed_state(
        device_id, timestamp, state
    ):
        state = {"consecutive": 0, "confirmed": False, "onset_time": None}
        onset_state[device_id] = state

    if state["confirmed"]:
        return {
            "sleep_prob": sleep_prob,
            "state": "CONFIRMED",
            "onset_time": state["onset_time"],
            "consecutive_above_threshold": state["consecutive"],
            "alarm_time": get_alarm(device_id),
        }

    if sleep_prob >= THRESHOLD:
        state["consecutive"] += 1
        if state["consecutive"] == 1:
            state["onset_time"] = timestamp

        if state["consecutive"] >= 2:
            state["confirmed"] = True
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO sleep_sessions (device_id, onset_time) VALUES (%s, %s)",
                    (device_id, state["onset_time"]),
                )
            alarm_time = schedule_alarm(device_id, state["onset_time"])
            return {
                "sleep_prob": sleep_prob,
                "state": "CONFIRMED",
                "onset_time": state["onset_time"],
                "consecutive_above_threshold": state["consecutive"],
                "alarm_time": alarm_time,
            }
    else:
        state["consecutive"] = 0
        state["onset_time"] = None

    return {
        "sleep_prob": sleep_prob,
        "state": "TRACKING",
        "onset_time": state["onset_time"],
        "consecutive_above_threshold": state["consecutive"],
        "alarm_time": None,
    }


# ======================== Routes ========================
@router.post("/model/upload", summary="Hot-swap the sleep model")
async def upload_model(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".pkl"):
        raise HTTPException(status_code=400, detail="Only .pkl files are accepted.")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = MODEL_FILE.with_suffix(".tmp")

    try:
        with open(tmp_path, "wb") as file_handle:
            shutil.copyfileobj(file.file, file_handle)

        try:
            candidate = _validate_model_instance(joblib.load(tmp_path))
        except Exception as exc:
            tmp_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=422,
                detail=f"File is not a valid scikit-learn model: {exc}",
            ) from exc

        shutil.move(str(tmp_path), str(MODEL_FILE))

        global model, model_load_attempted, _model_source_path
        model = candidate
        model_load_attempted = True
        _model_source_path = str(MODEL_FILE)

        model_type = type(candidate).__name__
        logging.info("Sleep model hot-swapped: %s loaded from upload.", model_type)
        return {
            "status": "ok",
            "message": "Model uploaded and activated successfully.",
            "model_type": model_type,
            "saved_to": _display_model_path(MODEL_FILE),
        }
    finally:
        tmp_path.unlink(missing_ok=True)


@router.get("/model/info", summary="Current model status")
def model_info():
    current_model = get_model()
    if current_model is None:
        return {
            "loaded": False,
            "model_type": None,
            "source_path": None,
            "model_file_exists": MODEL_FILE.exists(),
        }
    return {
        "loaded": True,
        "model_type": type(current_model).__name__,
        "source_path": (
            _display_model_path(Path(_model_source_path))
            if _model_source_path
            else None
        ),
        "model_file_exists": MODEL_FILE.exists(),
    }


def _insert_log_and_fetch_history(
    payload: LogPayload, magnitude: float
) -> tuple[int, list]:
    timestamp_str = payload.timestamp.isoformat()
    hour = payload.timestamp.hour
    minute = payload.timestamp.minute

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO logs (
                device_id, timestamp, charging, battery_level,
                accel_x, accel_y, accel_z, accel_magnitude,
                notification_count, hour, minute
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                payload.device_id,
                timestamp_str,
                payload.charging,
                payload.battery_level,
                payload.accel_x,
                payload.accel_y,
                payload.accel_z,
                magnitude,
                payload.notification_count,
                hour,
                minute,
            ),
        )
        inserted_id = cursor.fetchone()["id"]
        cursor.execute(
            "SELECT * FROM logs WHERE device_id = %s ORDER BY id DESC LIMIT 6",
            (payload.device_id,),
        )
        rows = [dict(row) for row in cursor.fetchall()]

    rows.reverse()
    return inserted_id, rows


def _perform_inference(rows: list, device_id: str) -> float:
    try:
        feature_vector = build_feature_vector(rows)
        sleep_prob = predict(feature_vector)
        return sleep_prob
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logging.exception("Telemetry inference failed for device %s", device_id)
        raise HTTPException(
            status_code=503, detail=f"Sleep inference failed: {exc}"
        ) from exc


def _update_sleep_prob(inserted_id: int, sleep_prob: float):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE logs SET sleep_prob = %s WHERE id = %s", (sleep_prob, inserted_id)
        )


@router.post("/logs/raw.log")
def create_log(payload: LogPayload):
    logging.info(
        "Incoming telemetry for %s at %s",
        payload.device_id,
        payload.timestamp.isoformat(),
    )

    magnitude = compute_magnitude(payload.accel_x, payload.accel_y, payload.accel_z)
    inserted_id, rows = _insert_log_and_fetch_history(payload, magnitude)

    if len(rows) < 2:
        return {"state": "INSUFFICIENT_DATA"}

    sleep_prob = _perform_inference(rows, payload.device_id)
    _update_sleep_prob(inserted_id, sleep_prob)

    timestamp_str = payload.timestamp.isoformat()
    return process_log(payload.device_id, timestamp_str, sleep_prob)
