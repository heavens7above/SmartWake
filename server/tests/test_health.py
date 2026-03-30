import requests
import pytest

API_KEY = "sk_live_smartwake_93f8e21a"
BASE_URL = "https://smartwake.up.railway.app"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

def test_server_online():
    """Verify that the FastAPI server is running and responding."""
    r = requests.get(f"{BASE_URL}/docs")
    assert r.status_code == 200, f"Server returned {r.status_code}"
    
def test_authentication():
    """Verify the API Key validation handles invalid logic."""
    r = requests.get(f"{BASE_URL}/dashboard", headers={"X-API-Key": "invalid_key"}, params={"device_id": "pytest_sim_device"})
    assert r.status_code in {401, 403}, f"Did not reject invalid auth: {r.status_code}"
