import logging
from fastapi import APIRouter
from datetime import datetime, timedelta
from src.modules.shared import WakeTimePayload, RegisterPayload, WakeAckPayload, get_db

router = APIRouter()

# ======================== Core Math ========================
def calculate_alarm(onset_time: str, wake_deadline: str, cycle_minutes: int = 90) -> str:
    onset = datetime.fromisoformat(onset_time)
    deadline = datetime.fromisoformat(wake_deadline)
    
    if deadline <= onset:
        return wake_deadline
    
    total_minutes = (deadline - onset).total_seconds() / 60.0
    cycles = int(total_minutes // cycle_minutes)
    if cycles <= 0:
        return deadline.isoformat()
    
    ideal_wake = onset + timedelta(minutes=cycles * cycle_minutes)
    
    gap_minutes = (deadline - ideal_wake).total_seconds() / 60.0
    return deadline.isoformat() if gap_minutes < 15 else ideal_wake.isoformat()

# ======================== Scheduler ========================
alarm_registry = {}

def schedule_alarm(device_id: str, onset_time: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM device_registry WHERE device_id = %s ORDER BY id DESC LIMIT 1', (device_id,))
        registry_row = cursor.fetchone()
        
        if not registry_row or not registry_row['wake_deadline']:
            return None
            
        wake_deadline = registry_row['wake_deadline']
        
        alarm_time = calculate_alarm(onset_time, wake_deadline)
        alarm_registry[device_id] = alarm_time
        
        cursor.execute('''
            UPDATE sleep_sessions 
            SET alarm_time = %s 
            WHERE device_id = %s AND onset_time = %s
        ''', (alarm_time, device_id, onset_time))
        conn.commit()
        
        return alarm_time

def get_alarm(device_id: str):
    if alarm_time := alarm_registry.get(device_id):
        return alarm_time

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT alarm_time
            FROM sleep_sessions
            WHERE device_id = %s AND alarm_time IS NOT NULL
            ORDER BY id DESC
            LIMIT 1
            ''',
            (device_id,),
        )
        row = cursor.fetchone()

    if row and row["alarm_time"]:
        alarm_registry[device_id] = row["alarm_time"]
        return row["alarm_time"]
    return None

# ======================== Routes ========================

@router.post("/register")
def register_device(payload: RegisterPayload):
    """Register a device on first launch. Upserts into device_registry."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO device_registry (device_id)
            VALUES (%s)
            ON CONFLICT(device_id) DO UPDATE SET
            registered_at=CURRENT_TIMESTAMP
        ''', (payload.device_id,))
        conn.commit()
    logging.info("Device registered: %s", payload.device_id)
    return {"device_id": payload.device_id, "registered": True}


@router.post("/wake-ack")
def wake_ack(payload: WakeAckPayload):
    """Acknowledge that the user woke up. Marks alarm_fired on the latest session and clears the in-memory alarm."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE sleep_sessions
            SET alarm_fired = TRUE
            WHERE id = (
                SELECT id FROM sleep_sessions
                WHERE device_id = %s
                ORDER BY id DESC LIMIT 1
            )
        ''', (payload.device_id,))
        conn.commit()

    # Clear the in-memory alarm so it doesn't re-fire
    alarm_registry.pop(payload.device_id, None)
    logging.info("Wake acknowledged for device: %s", payload.device_id)
    return {"status": "ok", "device_id": payload.device_id}


@router.post("/wake-time")
def set_wake_time(payload: WakeTimePayload):
    latest_onset_time = None
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO device_registry (device_id, wake_deadline)
            VALUES (%s, %s)
            ON CONFLICT(device_id) DO UPDATE SET
            wake_deadline=excluded.wake_deadline,
            registered_at=CURRENT_TIMESTAMP
        ''', (payload.device_id, payload.wake_deadline.isoformat()))
        cursor.execute(
            '''
            SELECT onset_time
            FROM sleep_sessions
            WHERE device_id = %s AND onset_time IS NOT NULL
            ORDER BY id DESC
            LIMIT 1
            ''',
            (payload.device_id,),
        )
        if session_row := cursor.fetchone():
            latest_onset_time = session_row["onset_time"]
        conn.commit()

    alarm_time = schedule_alarm(payload.device_id, latest_onset_time) if latest_onset_time else None
    return {
        "status": "success",
        "device_id": payload.device_id,
        "wake_deadline": payload.wake_deadline,
        "alarm_time": alarm_time,
    }

@router.get("/alarm-status")
def get_alarm_status(device_id: str):
    alarm_time = get_alarm(device_id)

    # Determine if the alarm should currently fire on the client
    should_fire = False
    if alarm_time:
        try:
            alarm_dt = datetime.fromisoformat(alarm_time)
            now = datetime.now(alarm_dt.tzinfo) if alarm_dt.tzinfo else datetime.now()
            if now >= alarm_dt:
                # Check if the session has already been acked
                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT alarm_fired FROM sleep_sessions
                        WHERE device_id = %s AND alarm_time IS NOT NULL
                        ORDER BY id DESC LIMIT 1
                    ''', (device_id,))
                    row = cursor.fetchone()
                    if row and not row['alarm_fired']:
                        should_fire = True
        except (ValueError, TypeError):
            pass

    return {
        "alarm_scheduled": alarm_time is not None,
        "alarm_time": alarm_time,
        "should_fire": should_fire,
    }
