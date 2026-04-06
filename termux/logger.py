import os
import json
import uuid
import time
import subprocess
import requests
import schedule
import logging
from datetime import datetime, timezone

logging.basicConfig(
    filename='smartwake.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("smartwake-logger")

SERVER_URL = os.getenv("SMARTWAKE_URL", "https://your-railway-url.up.railway.app")
API_KEY = os.getenv("SMARTWAKE_API_KEY", "sk_live_smartwake_93f8e21a")
DEVICE_ID_FILE = "device_id.txt"

def get_device_id():
    if os.path.exists(DEVICE_ID_FILE):
        with open(DEVICE_ID_FILE, "r") as f:
            return f.read().strip()
    else:
        new_id = str(uuid.uuid4())
        logger.info(f"Generated new unique DEVICE_ID: {new_id}")
        with open(DEVICE_ID_FILE, "w") as f:
            f.write(new_id)
        return new_id

DEVICE_ID = get_device_id()

def get_battery():
    try:
        res = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=5)
        data = json.loads(res.stdout)
        charging = data.get("status") == "CHARGING" or data.get("status") == "FULL"
        battery_level = int(data.get("percentage", 0))
        return charging, battery_level
    except Exception as e:
        logger.error(f"Failed to read battery: {e}")
        return False, 0

def get_accel():
    try:
        res = subprocess.run(["termux-sensor", "-s", "Accelerometer", "-n", "1"], capture_output=True, text=True, timeout=5)
        data = json.loads(res.stdout)
        for k in data:
            if "ccelerometer" in k or "Accelerometer" in k:
                sensor_key = k
                break
        else:
            sensor_key = next(iter(data), None)

        if not sensor_key: return 0.0, 0.0, 0.0
        values = data[sensor_key]["values"]
        return float(values[0]), float(values[1]), float(values[2])
    except Exception:
        return 0.0, 0.0, 0.0

def get_notification_count():
    try:
        res = subprocess.run(["termux-notification-list"], capture_output=True, text=True, timeout=5)
        data = json.loads(res.stdout)
        return len(data)
    except Exception:
        return 0

def log_cycle():
    try:
        charging, battery_level = get_battery()
        accel_x, accel_y, accel_z = get_accel()
        notification_count = get_notification_count()
        now = datetime.now(timezone.utc)
        
        payload = {
            "device_id": DEVICE_ID,
            "timestamp": now.isoformat(),
            "charging": charging,
            "battery_level": battery_level,
            "accel_x": accel_x,
            "accel_y": accel_y,
            "accel_z": accel_z,
            "notification_count": notification_count
        }
        
        res = requests.post(f"{SERVER_URL}/logs/raw.log", json=payload, headers={"X-API-Key": API_KEY}, timeout=10)
        res.raise_for_status()
        logger.info("Successfully pushed 5-minute cycle to server.")
    except Exception:
        logger.exception("Critical error in log_cycle loop")

def run():
    schedule.every(5).minutes.do(log_cycle)
    log_cycle()
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    run()
