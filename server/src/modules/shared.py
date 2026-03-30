import sqlite3
import os
import math
from contextlib import contextmanager
from pydantic import BaseModel, Field
from datetime import datetime

# ======================== Server Config ========================
# Single source of truth for the server's own public URL.
# Set BASE_URL in .env to your Railway / production domain.
# Falls back to localhost for local development.
def get_base_url() -> str:
    return os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")

BASE_URL: str = get_base_url()

# ======================== Utils ========================

def cyclical_encode(hour: int, minute: int):
    total_minutes = hour * 60 + minute
    sin_val = math.sin(2 * math.pi * total_minutes / 1440.0)
    cos_val = math.cos(2 * math.pi * total_minutes / 1440.0)
    return sin_val, cos_val

def compute_magnitude(x: float, y: float, z: float) -> float:
    return (x**2 + y**2 + z**2)**0.5

# ======================== Schemas ========================
class LogPayload(BaseModel):
    # CODEX-FIX: Reject empty device IDs so bad clients cannot poison the log table with anonymous rows.
    device_id: str = Field(min_length=1)
    timestamp: datetime
    charging: bool
    # CODEX-FIX: Constrain battery percentages to valid values instead of storing impossible numbers.
    battery_level: int = Field(ge=0, le=100)
    accel_x: float
    accel_y: float
    accel_z: float
    # CODEX-FIX: Reject negative notification counts that would corrupt derived feature calculations.
    notification_count: int = Field(ge=0)

class WakeTimePayload(BaseModel):
    # CODEX-FIX: Reject empty device IDs so wake-time updates always target a concrete device.
    device_id: str = Field(min_length=1)
    wake_deadline: datetime

class RatingPayload(BaseModel):
    # CODEX-FIX: Reject empty device IDs so ratings never update an unintended latest session.
    device_id: str = Field(min_length=1)
    # CODEX-FIX: Clamp sleep ratings to the supported 1-5 star range before they reach SQLite.
    quality_rating: int = Field(ge=1, le=5)

# ======================== Database ========================
def get_db_path():
    return os.getenv("DB_PATH", "db/smartwake.db")

@contextmanager
def get_db():
    db_path = get_db_path()
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                charging BOOLEAN NOT NULL,
                battery_level INTEGER NOT NULL,
                accel_x REAL NOT NULL,
                accel_y REAL NOT NULL,
                accel_z REAL NOT NULL,
                accel_magnitude REAL NOT NULL,
                notification_count INTEGER NOT NULL,
                hour INTEGER NOT NULL,
                minute INTEGER NOT NULL,
                sleep_prob REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sleep_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                onset_time TEXT,
                wake_deadline TEXT,
                alarm_time TEXT,
                alarm_fired BOOLEAN DEFAULT 0,
                quality_rating INTEGER,
                cycle_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS device_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL UNIQUE,
                wake_deadline TEXT,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
