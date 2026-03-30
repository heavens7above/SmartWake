import requests
import time
from datetime import datetime, timedelta, timezone
import random

API_KEY = "sk_live_smartwake_93f8e21a"
BASE_URL = "https://smartwake.up.railway.app"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
DEVICE_ID = "pytest_sim_device"

def test_wake_deadline_set():
    """Ensure the server registers a wake deadline correctly."""
    deadline = datetime.now(timezone.utc) + timedelta(hours=8)
    r = requests.post(f"{BASE_URL}/wake-time", headers=HEADERS, json={
        "device_id": DEVICE_ID,
        "wake_deadline": deadline.isoformat()
    })
    
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert data["device_id"] == DEVICE_ID

def test_sleep_simulation_pipeline():
    """Pump 10 realistic logs representing sleep into PostgreSQL telemetry and ensure ML model parses them seamlessly."""
    base_time = datetime(2026, 4, 1, 3, 0, 0, tzinfo=timezone.utc) 
    
    for minute in range(10):
        payload = {
            "device_id": DEVICE_ID,
            "timestamp": (base_time + timedelta(minutes=minute)).isoformat(),
            "charging": True, 
            "battery_level": 100,
            "accel_x": random.uniform(-0.01, 0.01),
            "accel_y": random.uniform(-0.01, 0.01),
            "accel_z": random.uniform(-0.01, 0.01), 
            "notification_count": 0
        }
        r = requests.post(f"{BASE_URL}/logs/raw.log", headers=HEADERS, json=payload)
        assert r.status_code == 200
        time.sleep(0.1)

def test_alarm_status_checkout():
    """Check if the previous simulated telemetry forced the ML model to calculate an explicit alarm time."""
    r = requests.get(f"{BASE_URL}/alarm-status", headers=HEADERS, params={"device_id": DEVICE_ID})
    assert r.status_code == 200
    data = r.json()
    assert data["alarm_scheduled"] is True 
    assert data["alarm_time"] is not None
