from fastapi import APIRouter, HTTPException
from src.modules.shared import RatingPayload, get_db

router = APIRouter()

# ======================== Routes ========================
@router.get("/dashboard")
def get_dashboard(device_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM sleep_sessions WHERE device_id = %s ORDER BY id DESC LIMIT 1', (device_id,))
        session_row = cursor.fetchone()
        cursor.execute('SELECT timestamp, sleep_prob, accel_magnitude, charging FROM logs WHERE device_id = %s ORDER BY id DESC LIMIT 48', (device_id,))
        log_rows = [dict(row) for row in cursor.fetchall()]
        
    session_data = dict(session_row) if session_row else None
    
    return {
        "device_id": device_id,
        "recent_session": session_data,
        "logs": log_rows
    }

@router.post("/rating")
def submit_rating(payload: RatingPayload):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE sleep_sessions
            SET quality_rating = %s
            WHERE id = (
                SELECT id FROM sleep_sessions
                WHERE device_id = %s
                ORDER BY id DESC LIMIT 1
            )
        ''', (payload.quality_rating, payload.device_id))
        updated = cursor.rowcount > 0
        conn.commit()
        
    if updated:
        return {"status": "success", "message": "Rating updated."}
    raise HTTPException(status_code=404, detail="No session found.")
