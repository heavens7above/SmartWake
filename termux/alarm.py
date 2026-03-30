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

SERVER_URL = "https://your-railway-url.up.railway.app" # User needs to update this
API_KEY = "sk_live_smartwake_93f8e21a" # Ensure this matches Server .env
DEVICE_ID_FILE = "device_id.txt"

def get_device_id():
    if os.path.exists(DEVICE_ID_FILE):
        with open(DEVICE_ID_FILE, "r") as f:
            return f.read().strip()
    return "UNKNOWN"

DEVICE_ID = get_device_id()
last_fired_date = None

def check_and_fire():
    global last_fired_date
    try:
        res = requests.get(f"{SERVER_URL}/alarm-status?device_id={DEVICE_ID}", headers={"X-API-Key": API_KEY}, timeout=10)
        res.raise_for_status()
        data = res.json()
        
        now = datetime.now()
        
        if last_fired_date is not None:
            if now.date() > last_fired_date and now.hour >= 12:
                last_fired_date = None
                
        if data.get("alarm_scheduled") and data.get("alarm_time"):
            alarm_dt = datetime.fromisoformat(data["alarm_time"])
            
            if now >= alarm_dt and last_fired_date is None:
                log.info(f"FIRING ALARM AT {now} (Scheduled for {alarm_dt})")
                subprocess.run(["termux-notification", "--priority", "high", "--title", "Wake Up", "--content", "End of sleep cycle"])
                subprocess.run(["termux-media-player", "play", "/sdcard/alarm.mp3"])
                subprocess.run(["termux-vibrate", "-d", "1000", "-f"])
                
                last_fired_date = now.date()
                
    except Exception as e:
        log.error(f"Failed to process alarm status: {e}")

def run():
    while True:
        check_and_fire()
        time.sleep(60)
        
if __name__ == "__main__":
    run()
