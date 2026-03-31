import os
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import PlainTextResponse
from src.modules.shared import BASE_URL

router = APIRouter(tags=["Deployment"])

# Resolved from the app's working directory (/app in container, server/ locally).
# server/termux/ is committed into the image so it's always present.
TERMUX_PATH = Path(__file__).resolve().parents[2] / "termux"

def _resolve_base_url(request: Request) -> str:
    """
    Returns the authoritative server base URL.
    Priority: BASE_URL env var (set in .env) > inferred from the incoming request.
    The env var wins so that proxied Railway deployments always return the correct
    public domain instead of an internal container IP.
    """
    env_url = BASE_URL
    if env_url and "localhost" not in env_url and "127.0.0.1" not in env_url:
        return env_url.rstrip("/")
    return str(request.base_url).rstrip("/")


@router.get("/install", response_class=PlainTextResponse)
def get_install_script(request: Request):
    """
    Returns the dynamic bash one-liner script that automates Termux.
    When users run `curl https://domain/install | bash`, this is executed.
    Script is environment-aware: Termux-specific commands only run on Android.
    """
    base_url = _resolve_base_url(request)

    return f"""#!/bin/bash
echo "[*] Initializing SmartWake Deployment..."
echo ""

# -- Detect environment --------------------------------------------------
IS_TERMUX=false
if [ -n "$PREFIX" ] && echo "$PREFIX" | grep -q "com.termux"; then
  IS_TERMUX=true
fi

if [ "$IS_TERMUX" = true ]; then
  echo "[+] Termux / Android environment detected"
else
  echo "[~] Non-Termux environment — skipping Android-specific steps"
fi
echo ""

# -- Termux only: system packages ----------------------------------------
if [ "$IS_TERMUX" = true ]; then
  echo ">> Updating Termux repositories..."
  pkg update -y && pkg upgrade -y
  echo ">> Installing Python & Termux-API..."
  pkg install python termux-api -y
fi

# -- Universal: Python packages ------------------------------------------
echo ">> Installing Python packages (requests, schedule)..."
pip install requests schedule --quiet

# -- Termux only: Android permissions ------------------------------------
if [ "$IS_TERMUX" = true ]; then
  echo ">> Requesting Android storage & sensor permissions..."
  termux-setup-storage
fi

# -- Download payload scripts --------------------------------------------
mkdir -p ~/smartwake
cd ~/smartwake
echo ">> Fetching payload scripts from SmartWake server..."
curl -sL {base_url}/termux/logger.py -o logger.py
curl -sL {base_url}/termux/alarm.py -o alarm.py
curl -sL {base_url}/termux/start.sh -o start.sh
chmod +x start.sh

echo ""
echo "=============================================="
echo "    DEPLOYMENT SUCCESSFUL!   "
echo "=============================================="
echo "To begin full telemetry monitoring, run:"
echo ""
echo "  cd ~/smartwake && bash start.sh"
echo ""
if [ "$IS_TERMUX" = true ]; then
  echo "Note: Place 'alarm.mp3' in /sdcard/alarm.mp3 before running."
fi
echo "=============================================="
"""

@router.get("/termux/{filename}", response_class=PlainTextResponse)
def get_termux_file(request: Request, filename: str):
    """
    Serves the python payloads directly, while dynamically injecting
    the authoritative BASE_URL into logger and alarm so the user
    never has to edit SERVER_URL manually.
    """
    allowed_files = ["logger.py", "alarm.py", "start.sh"]
    if filename not in allowed_files:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = TERMUX_PATH / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Payload file missing on server")

    with file_path.open("r", encoding="utf-8") as f:
        content = f.read()

    # Inject the live BASE_URL so the phone client is auto-configured
    if filename in {"logger.py", "alarm.py"}:
        base_url = _resolve_base_url(request)
        content = content.replace('"https://your-railway-url.up.railway.app"', f'"{base_url}"')
        content = content.replace("'https://your-railway-url.up.railway.app'", f'"{base_url}"')

    return content
