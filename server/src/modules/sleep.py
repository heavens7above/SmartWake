import os
import joblib
import logging
import numpy as np
from fastapi import APIRouter
from src.modules.shared import LogPayload, get_db, compute_magnitude, cyclical_encode
from src.modules.alarms import schedule_alarm

router = APIRouter()

# ======================== ML Inference & Features ========================
model = None

def get_model():
    global model
    if model is None:
        model_path = os.getenv("MODEL_PATH", "src/sleep_model.pkl") 
        if os.path.exists(model_path):
            model = joblib.load(model_path)
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

def process_log(device_id: str, timestamp: str, sleep_prob: float):
    if device_id not in onset_state:
        onset_state[device_id] = {"consecutive": 0, "confirmed": False, "onset_time": None}
    state = onset_state[device_id]
    
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
@router.post("/logs/raw.log")
def create_log(payload: LogPayload):
    payload_json = payload.model_dump_json()
    logging.info(f"Incoming Payload: {payload_json}")
    
    # Forcefully append payload to local physical debug text trace
    try:
        os.makedirs("logs", exist_ok=True)
        with open("logs/raw.log", "a") as f:
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
