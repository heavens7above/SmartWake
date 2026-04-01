import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException

from src.modules.shared import (
    RegisterPayload,
    WakeAckPayload,
    WakeTimePayload,
    get_db,
    normalize_datetime,
    normalize_device_id,
)

router = APIRouter()

# ======================== Core Math ========================
def calculate_alarm(onset_time: str, wake_deadline: str, cycle_minutes: int = 90) -> str:
    onset = normalize_datetime(datetime.fromisoformat(onset_time))
    deadline = normalize_datetime(datetime.fromisoformat(wake_deadline))

    if deadline <= onset:
        return deadline.isoformat()

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
        cursor.execute(
            """
            SELECT wake_deadline
            FROM device_registry
            WHERE device_id = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (device_id,),
        )
        registry_row = cursor.fetchone()

        if not registry_row or not registry_row["wake_deadline"]:
            alarm_registry.pop(device_id, None)
            return None

        wake_deadline = registry_row["wake_deadline"]
        alarm_time = calculate_alarm(onset_time, wake_deadline)
        alarm_registry[device_id] = alarm_time

        cursor.execute(
            """
            UPDATE sleep_sessions
            SET wake_deadline = %s, alarm_time = %s
            WHERE id = (
                SELECT id
                FROM sleep_sessions
                WHERE device_id = %s AND onset_time = %s
                ORDER BY id DESC
                LIMIT 1
            )
            """,
            (wake_deadline, alarm_time, device_id, onset_time),
        )
        return alarm_time


def get_alarm(device_id: str):
    if alarm_time := alarm_registry.get(device_id):
        return alarm_time

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT alarm_time
            FROM sleep_sessions
            WHERE device_id = %s AND alarm_time IS NOT NULL AND alarm_fired = FALSE
            ORDER BY id DESC
            LIMIT 1
            """,
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
        cursor.execute(
            """
            INSERT INTO device_registry (device_id)
            VALUES (%s)
            ON CONFLICT(device_id) DO UPDATE SET
            registered_at = CURRENT_TIMESTAMP
            """,
            (payload.device_id,),
        )
    logging.info("Device registered: %s", payload.device_id)
    return {"device_id": payload.device_id, "registered": True}


@router.post("/wake-ack")
def wake_ack(payload: WakeAckPayload):
    """Acknowledge that the user woke up and prevent the alarm from re-firing."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE sleep_sessions
            SET alarm_fired = TRUE
            WHERE id = (
                SELECT id
                FROM sleep_sessions
                WHERE device_id = %s AND alarm_fired = FALSE
                ORDER BY id DESC
                LIMIT 1
            )
            """,
            (payload.device_id,),
        )
        acknowledged = cursor.rowcount > 0

    alarm_registry.pop(payload.device_id, None)
    logging.info("Wake acknowledged for device: %s", payload.device_id)
    return {
        "status": "ok",
        "device_id": payload.device_id,
        "acknowledged": acknowledged,
    }


@router.post("/wake-time")
def set_wake_time(payload: WakeTimePayload):
    latest_onset_time = None
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO device_registry (device_id, wake_deadline)
            VALUES (%s, %s)
            ON CONFLICT(device_id) DO UPDATE SET
            wake_deadline = excluded.wake_deadline,
            registered_at = CURRENT_TIMESTAMP
            """,
            (payload.device_id, payload.wake_deadline.isoformat()),
        )
        cursor.execute(
            """
            SELECT onset_time
            FROM sleep_sessions
            WHERE device_id = %s AND onset_time IS NOT NULL
            ORDER BY id DESC
            LIMIT 1
            """,
            (payload.device_id,),
        )
        if session_row := cursor.fetchone():
            latest_onset_time = session_row["onset_time"]

    alarm_time = schedule_alarm(payload.device_id, latest_onset_time) if latest_onset_time else None
    return {
        "status": "success",
        "device_id": payload.device_id,
        "wake_deadline": payload.wake_deadline,
        "alarm_time": alarm_time,
    }


@router.get("/alarm-status")
def get_alarm_status(device_id: str):
    try:
        device_id = normalize_device_id(device_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    alarm_time = get_alarm(device_id)

    should_fire = False
    if alarm_time:
        try:
            alarm_dt = normalize_datetime(datetime.fromisoformat(alarm_time))
            now = datetime.now(timezone.utc)
            if now >= alarm_dt:
                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        SELECT alarm_fired
                        FROM sleep_sessions
                        WHERE device_id = %s AND alarm_time IS NOT NULL
                        ORDER BY id DESC
                        LIMIT 1
                        """,
                        (device_id,),
                    )
                    row = cursor.fetchone()
                    if row and not row["alarm_fired"]:
                        should_fire = True
        except (TypeError, ValueError):
            logging.warning("Invalid alarm timestamp stored for device %s: %s", device_id, alarm_time)

    return {
        "alarm_scheduled": alarm_time is not None,
        "alarm_time": alarm_time,
        "should_fire": should_fire,
    }
