#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

SMARTWAKE_URL="${SMARTWAKE_URL:-https://your-railway-url.up.railway.app}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[!] Missing required command: $1" >&2
    exit 1
  fi
}

cleanup() {
  if [[ -n "${LOGGER_PID:-}" ]]; then
    kill "$LOGGER_PID" 2>/dev/null || true
  fi
  if [[ -n "${ALARM_PID:-}" ]]; then
    kill "$ALARM_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

require_command python
require_command curl
require_command termux-wake-lock

echo "[*] Acquiring wake lock..."
termux-wake-lock

echo "[*] Checking SmartWake server..."
if ! curl -fsS --max-time 10 "${SMARTWAKE_URL}/health" >/dev/null; then
  echo "[!] Server health check failed: ${SMARTWAKE_URL}/health" >&2
  exit 1
fi

echo "[*] Starting telemetry worker..."
python logger.py &
LOGGER_PID=$!

echo "[*] Starting alarm worker..."
python alarm.py &
ALARM_PID=$!

while true; do
  if ! kill -0 "$LOGGER_PID" 2>/dev/null; then
    wait "$LOGGER_PID"
    exit $?
  fi
  if ! kill -0 "$ALARM_PID" 2>/dev/null; then
    wait "$ALARM_PID"
    exit $?
  fi
  sleep 5
done
