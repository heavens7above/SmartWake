import os
import time
import requests
import subprocess
import logging
from datetime import datetime

logging.basicConfig(
    filename='smartwake.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("smartwake-alarm")

SERVER_URL = os.getenv("SMARTWAKE_URL", "https://your-railway-url.up.railway.app")
API_KEY = os.getenv("SMARTWAKE_API_KEY", "sk_live_smartwake_93f8e21a")
DEVICE_ID_FILE = "device_id.txt"

def get_device_id():
    if os.path.exists(DEVICE_ID_FILE):
        with open(DEVICE_ID_FILE, "r") as f:
            return f.read().strip()
    return "UNKNOWN"

DEVICE_ID = get_device_id()
last_fired_alarm_time = None

def check_and_fire():
    global last_fired_alarm_time
    try:
        res = requests.get(f"{SERVER_URL}/alarm-status?device_id={DEVICE_ID}", headers={"X-API-Key": API_KEY}, timeout=10)
        res.raise_for_status()
        data = res.json()
        
        now = datetime.now()
        alarm_time = data.get("alarm_time")

        if data.get("alarm_scheduled") and alarm_time:
            alarm_dt = datetime.fromisoformat(alarm_time)
            
            if now >= alarm_dt and last_fired_alarm_time != alarm_time:
                log.info(f"FIRING ALARM AT {now} (Scheduled for {alarm_dt})")
                subprocess.run(["termux-notification", "--priority", "high", "--title", "Wake Up", "--content", "End of sleep cycle"])
                subprocess.run(["termux-media-player", "play", "/sdcard/alarm.mp3"])
                subprocess.run(["termux-vibrate", "-d", "1000", "-f"])
                
                last_fired_alarm_time = alarm_time
                
    except Exception as e:
        log.error(f"Failed to process alarm status: {e}")

def run():
    while True:
        check_and_fire()
        time.sleep(60)
        
if __name__ == "__main__":
    run()
