from fastapi import APIRouter
from datetime import datetime, timedelta
from src.modules.shared import WakeTimePayload, get_db

router = APIRouter()

# ======================== Core Math ========================
def calculate_alarm(onset_time: str, wake_deadline: str, cycle_minutes: int = 90) -> str:
    onset = datetime.fromisoformat(onset_time)
    deadline = datetime.fromisoformat(wake_deadline)
    
    if deadline <= onset:
        return wake_deadline
    
    total_minutes = (deadline - onset).total_seconds() / 60.0
    cycles = int(total_minutes // cycle_minutes)
    
    ideal_wake = onset + timedelta(minutes=cycles * cycle_minutes)
    
    gap_minutes = (deadline - ideal_wake).total_seconds() / 60.0
    if gap_minutes < 15:
        return deadline.isoformat()
        
    return ideal_wake.isoformat()

# ======================== Scheduler ========================
alarm_registry = {}

def schedule_alarm(device_id: str, onset_time: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM device_registry WHERE device_id = ? ORDER BY id DESC LIMIT 1', (device_id,))
        registry_row = cursor.fetchone()
        
        if not registry_row or not registry_row['wake_deadline']:
            return None
            
        wake_deadline = registry_row['wake_deadline']
        
        alarm_time = calculate_alarm(onset_time, wake_deadline)
        alarm_registry[device_id] = alarm_time
        
        cursor.execute('''
            UPDATE sleep_sessions 
            SET alarm_time = ? 
            WHERE device_id = ? AND onset_time = ?
        ''', (alarm_time, device_id, onset_time))
        conn.commit()
        
        return alarm_time

def get_alarm(device_id: str):
    return alarm_registry.get(device_id)

# ======================== Routes ========================
@router.post("/wake-time")
def set_wake_time(payload: WakeTimePayload):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO device_registry (device_id, wake_deadline)
            VALUES (?, ?)
            ON CONFLICT(device_id) DO UPDATE SET
            wake_deadline=excluded.wake_deadline,
            registered_at=CURRENT_TIMESTAMP
        ''', (payload.device_id, payload.wake_deadline.isoformat()))
        conn.commit()
        
    return {"status": "success", "device_id": payload.device_id, "wake_deadline": payload.wake_deadline}

@router.get("/alarm-status")
def get_alarm_status(device_id: str):
    alarm_time = get_alarm(device_id)
    return {
        "alarm_scheduled": alarm_time is not None,
        "alarm_time": alarm_time
    }
