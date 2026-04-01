import os
import time
import requests
import subprocess
import logging
from datetime import datetime, timezone

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

def _parse_alarm_time(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)

def _run_termux_command(command):
    try:
        subprocess.run(command, check=False, timeout=15)
    except Exception as exc:
        log.warning("Command failed (%s): %s", " ".join(command), exc)

def _ack_alarm():
    try:
        res = requests.post(
            f"{SERVER_URL}/wake-ack",
            json={"device_id": DEVICE_ID},
            headers={"X-API-Key": API_KEY},
            timeout=10,
        )
        res.raise_for_status()
        return True
    except requests.RequestException as exc:
        log.warning("Alarm fired locally but wake acknowledgement failed: %s", exc)
        return False

def check_and_fire():
    global last_fired_alarm_time
    try:
        res = requests.get(
            f"{SERVER_URL}/alarm-status?device_id={DEVICE_ID}",
            headers={"X-API-Key": API_KEY},
            timeout=10,
        )
        res.raise_for_status()
        data = res.json()

        now = datetime.now(timezone.utc)
        alarm_time = data.get("alarm_time")

        if data.get("alarm_scheduled") and alarm_time:
            alarm_dt = _parse_alarm_time(alarm_time)
            if alarm_dt is None:
                log.warning("Ignoring malformed alarm_time value: %s", alarm_time)
                return

            if now >= alarm_dt and last_fired_alarm_time != alarm_time:
                log.info(f"FIRING ALARM AT {now} (Scheduled for {alarm_dt})")
                _run_termux_command([
                    "termux-notification",
                    "--priority",
                    "high",
                    "--title",
                    "Wake Up",
                    "--content",
                    "End of sleep cycle",
                ])
                _run_termux_command(["termux-media-player", "play", "/sdcard/alarm.mp3"])
                _run_termux_command(["termux-vibrate", "-d", "1000", "-f"])

                last_fired_alarm_time = alarm_time
                _ack_alarm()
    except requests.RequestException as exc:
        log.warning("Failed to process alarm status: %s", exc)
    except Exception:
        log.exception("Unexpected alarm worker failure")

def run():
    while True:
        check_and_fire()
        time.sleep(60)
        
if __name__ == "__main__":
    run()
