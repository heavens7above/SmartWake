import logging
import math
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

import psycopg2
import psycopg2.extras
import psycopg2.pool
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ======================== Server Config ========================
APP_ROOT = Path(__file__).resolve().parents[2]
DB_SCHEMA_FILE = APP_ROOT / "db" / "schema.sql"


def get_base_url() -> str:
    return os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")


BASE_URL: str = get_base_url()

# ======================== Utils ========================
def normalize_device_id(value: str) -> str:
    device_id = value.strip()
    if not device_id:
        raise ValueError("device_id must not be blank")
    return device_id


def normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def cyclical_encode(hour: int, minute: int):
    total_minutes = hour * 60 + minute
    sin_val = math.sin(2 * math.pi * total_minutes / 1440.0)
    cos_val = math.cos(2 * math.pi * total_minutes / 1440.0)
    return sin_val, cos_val


def compute_magnitude(x: float, y: float, z: float) -> float:
    return (x**2 + y**2 + z**2) ** 0.5


# ======================== Schemas ========================
class SmartWakePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DevicePayload(SmartWakePayload):
    device_id: str = Field(min_length=1)

    @field_validator("device_id")
    @classmethod
    def validate_device_id(cls, value: str) -> str:
        return normalize_device_id(value)


class LogPayload(DevicePayload):
    timestamp: datetime
    charging: bool
    battery_level: int = Field(ge=0, le=100)
    accel_x: float
    accel_y: float
    accel_z: float
    notification_count: int = Field(ge=0)

    @model_validator(mode="before")
    @classmethod
    def normalize_accelerometer_payload(cls, data):
        if not isinstance(data, dict):
            return data

        normalized = dict(data)
        accelerometer = normalized.pop("accelerometer", None)
        if accelerometer is None:
            return normalized

        if not isinstance(accelerometer, (list, tuple)):
            raise ValueError("accelerometer must be an array [x, y, z]")
        if len(accelerometer) != 3:
            raise ValueError("accelerometer must contain exactly three values [x, y, z]")

        normalized.setdefault("accel_x", accelerometer[0])
        normalized.setdefault("accel_y", accelerometer[1])
        normalized.setdefault("accel_z", accelerometer[2])
        return normalized

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return normalize_datetime(value)

    @field_validator("accel_x", "accel_y", "accel_z")
    @classmethod
    def validate_accel_component(cls, value: float, info) -> float:
        if not math.isfinite(value):
            raise ValueError(f"{info.field_name} must be a finite number")
        if abs(value) > 100.0:
            raise ValueError(f"{info.field_name} must be between -100 and 100 m/s^2")
        return value


class WakeTimePayload(DevicePayload):
    wake_deadline: datetime

    @field_validator("wake_deadline")
    @classmethod
    def validate_wake_deadline(cls, value: datetime) -> datetime:
        return normalize_datetime(value)


class RatingPayload(DevicePayload):
    quality_rating: int = Field(ge=1, le=5)


class RegisterPayload(DevicePayload):
    pass


class WakeAckPayload(DevicePayload):
    pass


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
            raise RuntimeError(
                "Either DATABASE_URL or DB_PASSWORD environment variables must be set"
            )

        safe_user = quote_plus(user)
        safe_password = quote_plus(password)
        url = f"postgresql://{safe_user}:{safe_password}@{host}:{port}/{dbname}"

    # Railway sometimes emits postgres:// — psycopg2 requires postgresql://
    return url.replace("postgres://", "postgresql://", 1)


DB_POOL = None


def init_pool():
    global DB_POOL
    if DB_POOL is None:
        logging.info("Initializing PostgreSQL ThreadedConnectionPool (min=1, max=20)")
        DB_POOL = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=20,
            dsn=get_db_url(),
            cursor_factory=psycopg2.extras.RealDictCursor,
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
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        DB_POOL.putconn(conn)


def init_db():
    if not DB_SCHEMA_FILE.exists():
        raise RuntimeError(f"Database schema file is missing: {DB_SCHEMA_FILE}")

    schema_sql = DB_SCHEMA_FILE.read_text(encoding="utf-8")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(schema_sql)
