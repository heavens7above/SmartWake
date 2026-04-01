import importlib
import sys

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api_key() -> str:
    return "test-api-key"


@pytest.fixture
def client(monkeypatch, api_key):
    monkeypatch.setenv("API_KEY", api_key)
    monkeypatch.setenv("BASE_URL", "https://smartwake.test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://smartwake:smartwake@localhost:5432/smartwake")

    for module_name in [
        "main",
        "src.modules.shared",
        "src.modules.sleep",
        "src.modules.alarms",
        "src.modules.dashboards",
        "src.modules.termux",
    ]:
        sys.modules.pop(module_name, None)

    shared = importlib.import_module("src.modules.shared")
    monkeypatch.setattr(shared, "init_pool", lambda: None)
    monkeypatch.setattr(shared, "init_db", lambda: None)
    monkeypatch.setattr(shared, "close_pool", lambda: None)

    main = importlib.import_module("main")

    with TestClient(main.app) as test_client:
        yield test_client
