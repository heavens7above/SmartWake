import os
import math
from contextlib import contextmanager
from pydantic import BaseModel, Field
from datetime import datetime
import psycopg2
import psycopg2.extras

# ======================== Server Config ========================
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
    device_id: str = Field(min_length=1)
    timestamp: datetime
    charging: bool
    battery_level: int = Field(ge=0, le=100)
    accel_x: float
    accel_y: float
    accel_z: float
    notification_count: int = Field(ge=0)

class WakeTimePayload(BaseModel):
    device_id: str = Field(min_length=1)
    wake_deadline: datetime

class RatingPayload(BaseModel):
    device_id: str = Field(min_length=1)
    quality_rating: int = Field(ge=1, le=5)

# ======================== Database ========================
def get_db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        user = os.getenv("DB_USER", "postgres")
        password = os.getenv("DB_PASSWORD")
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        dbname = os.getenv("DB_NAME", "postgres")
        
        if not password:
            raise RuntimeError("Either DATABASE_URL or DB_PASSWORD environment variables must be set")
            
        url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        
    # Railway sometimes emits postgres:// — psycopg2 requires postgresql://
    return url.replace("postgres://", "postgresql://", 1)

from psycopg2 import pool
import logging

DB_POOL = None

def init_pool():
    global DB_POOL
    if DB_POOL is None:
        logging.info("Initializing PostgreSQL ThreadedConnectionPool (min=1, max=20)")
        DB_POOL = psycopg2.pool.ThreadedConnectionPool(
            minconn=1, maxconn=20, dsn=get_db_url(), cursor_factory=psycopg2.extras.RealDictCursor
        )

def close_pool():
    global DB_POOL
    if DB_POOL is not None:
        logging.info("Closing PostgreSQL Connection Pool")
        DB_POOL.closeall()
        DB_POOL = None

@contextmanager
def get_db():
    if DB_POOL is None:
        raise RuntimeError("Database pool not initialized. Call init_pool() on startup.")
    
    conn = DB_POOL.getconn()
    try:
        yield conn
        conn.commit() # Ensure stray inserts are committed before returning to pool
    except Exception:
        conn.rollback()
        raise
    finally:
        DB_POOL.putconn(conn)

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id                  SERIAL PRIMARY KEY,
                device_id           TEXT NOT NULL,
                timestamp           TEXT NOT NULL,
                charging            BOOLEAN NOT NULL,
                battery_level       INTEGER NOT NULL,
                accel_x             REAL NOT NULL,
                accel_y             REAL NOT NULL,
                accel_z             REAL NOT NULL,
                accel_magnitude     REAL NOT NULL,
                notification_count  INTEGER NOT NULL,
                hour                INTEGER NOT NULL,
                minute              INTEGER NOT NULL,
                sleep_prob          REAL,
                created_at          TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sleep_sessions (
                id              SERIAL PRIMARY KEY,
                device_id       TEXT NOT NULL,
                onset_time      TEXT,
                wake_deadline   TEXT,
                alarm_time      TEXT,
                alarm_fired     BOOLEAN DEFAULT FALSE,
                quality_rating  INTEGER,
                cycle_count     INTEGER,
                created_at      TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS device_registry (
                id              SERIAL PRIMARY KEY,
                device_id       TEXT NOT NULL UNIQUE,
                wake_deadline   TEXT,
                registered_at   TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        conn.commit()
