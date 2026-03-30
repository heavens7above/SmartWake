import os
import contextlib
import shutil
import joblib
import logging
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import APIRouter, UploadFile, File, HTTPException
from src.modules.shared import LogPayload, get_db, compute_magnitude, cyclical_encode
from src.modules.alarms import schedule_alarm

router = APIRouter()

# Canonical model location — always written/read here
MODEL_DIR  = Path("src/model")
MODEL_FILE = MODEL_DIR / "sleep_model.pkl"

# ======================== ML Inference & Features ========================
model = None
model_load_attempted = False
_model_source_path: str | None = None   # tracks which file is currently loaded

def _candidate_model_paths():
    """Search the known model locations so config/path drift does not silently disable inference."""
    configured = os.getenv("MODEL_PATH")
    candidates = []
    if configured:
        candidates.append(Path(configured))
    # canonical location first so uploads are always preferred
    candidates.extend([
        MODEL_FILE,
        Path("src/ml/sleep_model.pkl"),
        Path("src/sleep_model.pkl"),
    ])
    seen, unique = set(), []
    for c in candidates:
        key = str(c)
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique

def get_model(force_reload: bool = False):
    """Return the cached model, loading from disk on first call or when *force_reload* is True."""
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
            model = joblib.load(model_path)
            _model_source_path = str(model_path)
            logging.info("Loaded sleep model from %s", model_path)
            break
        except Exception:
            logging.exception("Failed to load sleep model from %s", model_path)

    if model is None:
        logging.warning("Sleep model not found; inference will return 0.0 until a model is uploaded.")
    return model

def predict(feature_vector) -> float:
    m = get_model()
    if m is None:
        return 0.0
    probs = m.predict_proba(feature_vector)
    return float(probs[0][1])

def build_feature_vector(rows: list) -> np.ndarray:
    if not rows:
        return np.zeros((1, 9))
    mags = np.array([r['accel_magnitude'] for r in rows])
    accel_magnitude_mean = np.mean(mags)
    accel_magnitude_std = np.std(mags)
    accel_magnitude_max = np.max(mags)
    
    if len(mags) > 1 and accel_magnitude_std > 0:
        mean_centered = mags - accel_magnitude_mean
        zero_crossings = np.sum(np.diff(np.sign(mean_centered)) != 0)
        zero_crossing_rate = zero_crossings / len(mags)
    else:
        zero_crossing_rate = 0.0
        
    notification_delta = rows[-1]['notification_count'] - rows[0]['notification_count']
    consecutive_still_count = 0
    for r in reversed(rows):
        if r['accel_magnitude'] < 0.05:
            consecutive_still_count += 1
        else:
            break
            
    charging = 1 if rows[-1]['charging'] else 0
    hour_sin, hour_cos = cyclical_encode(rows[-1]['hour'], rows[-1]['minute'])
    
    features = [
        accel_magnitude_mean, accel_magnitude_std, accel_magnitude_max,
        zero_crossing_rate, notification_delta, consecutive_still_count,
        charging, hour_sin, hour_cos
    ]
    return np.array([features])

# ======================== Onset State Machine ========================
onset_state = {}
THRESHOLD = 0.75

# CODEX-FIX: Reset stale confirmed sessions so one night's onset does not keep every later log permanently stuck in CONFIRMED.
def _should_reset_confirmed_state(device_id: str, timestamp: str, state: dict) -> bool:
    onset_time = state.get("onset_time")
    if not onset_time:
        return True

    try:
        current_dt = datetime.fromisoformat(timestamp)
        onset_dt = datetime.fromisoformat(onset_time)
    except ValueError:
        return True

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT COALESCE(alarm_time, wake_deadline) AS reset_time
            FROM sleep_sessions
            WHERE device_id = ?
            ORDER BY id DESC
            LIMIT 1
            ''',
            (device_id,),
        )
        session_row = cursor.fetchone()

    if session_row and session_row["reset_time"]:
        with contextlib.suppress(ValueError):
            return current_dt >= datetime.fromisoformat(session_row["reset_time"])

    return current_dt - onset_dt >= timedelta(hours=16)

def process_log(device_id: str, timestamp: str, sleep_prob: float):
    if device_id not in onset_state:
        onset_state[device_id] = {"consecutive": 0, "confirmed": False, "onset_time": None}
    state = onset_state[device_id]

    if state["confirmed"] and _should_reset_confirmed_state(device_id, timestamp, state):
        state = {"consecutive": 0, "confirmed": False, "onset_time": None}
        onset_state[device_id] = state
    
    if state["confirmed"]:
        return {"sleep_prob": sleep_prob, "state": "CONFIRMED", "onset_time": state["onset_time"], "consecutive_above_threshold": state["consecutive"]}
        
    if sleep_prob >= THRESHOLD:
        state["consecutive"] += 1
        if state["consecutive"] == 1:
            state["onset_time"] = timestamp
            
        if state["consecutive"] >= 2:
            state["confirmed"] = True
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO sleep_sessions (device_id, onset_time) VALUES (?, ?)', (device_id, state["onset_time"]))
                conn.commit()
            schedule_alarm(device_id, state["onset_time"])
            return {"sleep_prob": sleep_prob, "state": "CONFIRMED", "onset_time": state["onset_time"], "consecutive_above_threshold": state["consecutive"]}
    else:
        state["consecutive"] = 0
        state["onset_time"] = None
        
    return {"sleep_prob": sleep_prob, "state": "TRACKING", "onset_time": state["onset_time"], "consecutive_above_threshold": state["consecutive"]}

# ======================== Routes ========================

@router.post("/model/upload", summary="Hot-swap the sleep model")
async def upload_model(file: UploadFile = File(...)):
    """
    Upload a new sleep_model.pkl produced by the Colab training notebook.
    The file is validated, saved to the canonical path, and hot-reloaded
    into memory — no server restart required.
    """
    if not file.filename or not file.filename.endswith(".pkl"):
        raise HTTPException(status_code=400, detail="Only .pkl files are accepted.")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = MODEL_FILE.with_suffix(".tmp")

    try:
        # Write to a temp file first so an interrupted upload never corrupts the live model
        with open(tmp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Validate the file is a loadable model before committing
        try:
            candidate = joblib.load(tmp_path)
        except Exception as exc:
            tmp_path.unlink(missing_ok=True)
            raise HTTPException(status_code=422, detail=f"File is not a valid scikit-learn model: {exc}") from exc

        # Commit
        shutil.move(str(tmp_path), str(MODEL_FILE))

        # Hot-reload into RAM
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
            "saved_to": str(MODEL_FILE),
        }
    finally:
        tmp_path.unlink(missing_ok=True)  # clean up if something went wrong


@router.get("/model/info", summary="Current model status")
def model_info():
    """Return metadata about the currently loaded sleep model."""
    m = get_model()   # loads lazily if not yet attempted
    if m is None:
        return {
            "loaded": False,
            "model_type": None,
            "source_path": None,
            "model_file_exists": MODEL_FILE.exists(),
        }
    return {
        "loaded": True,
        "model_type": type(m).__name__,
        "source_path": _model_source_path,
        "model_file_exists": MODEL_FILE.exists(),
    }


@router.post("/logs/raw.log")
def create_log(payload: LogPayload):
    payload_json = payload.model_dump_json()
    logging.info(f"Incoming Payload: {payload_json}")
    
    # Forcefully append payload to local physical debug text trace
    try:
        os.makedirs("logs", exist_ok=True)
        # CODEX-FIX: Write logs with an explicit encoding so debug capture is stable across host locales.
        with open("logs/raw.log", "a", encoding="utf-8") as f:
            f.write(payload_json + "\\n")
    except Exception as e:
        logging.warning(f"Could not write to logs/raw.log: {e}")
        
    magnitude = compute_magnitude(payload.accel_x, payload.accel_y, payload.accel_z)
    timestamp_str = payload.timestamp.isoformat()
    hour = payload.timestamp.hour
    minute = payload.timestamp.minute
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO logs (
                device_id, timestamp, charging, battery_level, 
                accel_x, accel_y, accel_z, accel_magnitude, 
                notification_count, hour, minute
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            payload.device_id, timestamp_str, payload.charging, payload.battery_level,
            payload.accel_x, payload.accel_y, payload.accel_z, magnitude,
            payload.notification_count, hour, minute
        ))
        conn.commit()
        inserted_id = cursor.lastrowid
        
        cursor.execute('SELECT * FROM logs WHERE device_id = ? ORDER BY id DESC LIMIT 6', (payload.device_id,))
        rows = [dict(row) for row in cursor.fetchall()]
        
    rows.reverse()
    
    if len(rows) < 2:
        return {"state": "INSUFFICIENT_DATA"}
        
    feature_vector = build_feature_vector(rows)
    sleep_prob = predict(feature_vector)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE logs SET sleep_prob = ? WHERE id = ?', (sleep_prob, inserted_id))
        conn.commit()
        
    return process_log(payload.device_id, timestamp_str, sleep_prob)
