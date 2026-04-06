from contextlib import contextmanager

import pytest


class FakeCursor:
    def __init__(self, *, fetchone_results=None, fetchall_results=None, rowcount=0):
        self._fetchone_results = list(fetchone_results or [])
        self._fetchall_results = list(fetchall_results or [])
        self.executed = []
        self.rowcount = rowcount

    def execute(self, query, params=None):
        self.executed.append((" ".join(query.split()), params))

    def fetchone(self):
        return self._fetchone_results.pop(0) if self._fetchone_results else None

    def fetchall(self):
        return self._fetchall_results.pop(0) if self._fetchall_results else []


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def commit(self):
        pass

    def rollback(self):
        pass


def fake_get_db(*connections):
    queue = list(connections)

    @contextmanager
    def _get_db():
        if not queue:
            raise AssertionError("No fake database connection left for test")
        yield queue.pop(0)

    return _get_db


@pytest.fixture(autouse=True)
def _patch_dashboards_db():
    import sys

    if "src.modules.dashboards" in sys.modules:
        return sys.modules["src.modules.dashboards"]

    import src.modules.dashboards as dashboards

    return dashboards


def test_get_dashboard_success(client, api_key, monkeypatch, _patch_dashboards_db):
    dashboards = _patch_dashboards_db
    session_row = {"id": 1, "device_id": "pytest_sim_device", "quality_rating": 4}
    log_rows = [
        {
            "timestamp": "2026-04-01T03:00:00Z",
            "sleep_prob": 0.9,
            "accel_magnitude": 0.01,
            "charging": True,
        }
    ]
    cursor = FakeCursor(fetchone_results=[session_row], fetchall_results=[log_rows])

    monkeypatch.setattr(dashboards, "get_db", fake_get_db(FakeConnection(cursor)))

    response = client.get(
        "/dashboard?device_id=pytest_sim_device",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    assert response.json() == {
        "device_id": "pytest_sim_device",
        "recent_session": session_row,
        "logs": log_rows,
    }
    assert len(cursor.executed) == 2


def test_get_dashboard_no_session(client, api_key, monkeypatch, _patch_dashboards_db):
    dashboards = _patch_dashboards_db
    cursor = FakeCursor(fetchone_results=[None], fetchall_results=[[]])

    monkeypatch.setattr(dashboards, "get_db", fake_get_db(FakeConnection(cursor)))

    response = client.get(
        "/dashboard?device_id=pytest_sim_device",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    assert response.json() == {
        "device_id": "pytest_sim_device",
        "recent_session": None,
        "logs": [],
    }
    assert len(cursor.executed) == 2


def test_get_dashboard_invalid_device_id(client, api_key):
    response = client.get(
        "/dashboard?device_id=   ",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 422
    assert "device_id must not be blank" in response.text


def test_submit_rating_success(client, api_key, monkeypatch, _patch_dashboards_db):
    dashboards = _patch_dashboards_db
    cursor = FakeCursor(rowcount=1)

    monkeypatch.setattr(dashboards, "get_db", fake_get_db(FakeConnection(cursor)))

    response = client.post(
        "/rating",
        headers={"X-API-Key": api_key},
        json={"device_id": "pytest_sim_device", "quality_rating": 5},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Rating updated."}
    assert cursor.executed[0][1] == (5, "pytest_sim_device")


def test_submit_rating_not_found(client, api_key, monkeypatch, _patch_dashboards_db):
    dashboards = _patch_dashboards_db
    cursor = FakeCursor(rowcount=0)

    monkeypatch.setattr(dashboards, "get_db", fake_get_db(FakeConnection(cursor)))

    response = client.post(
        "/rating",
        headers={"X-API-Key": api_key},
        json={"device_id": "pytest_sim_device", "quality_rating": 3},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "No session found."


def test_submit_rating_invalid_rating(client, api_key):
    response = client.post(
        "/rating",
        headers={"X-API-Key": api_key},
        json={"device_id": "pytest_sim_device", "quality_rating": 6},
    )

    assert response.status_code == 422
    assert "quality_rating" in response.text
