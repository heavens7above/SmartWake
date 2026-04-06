from contextlib import contextmanager
from datetime import datetime, timezone

import pytest

import src.modules.alarms as alarms


class FakeCursor:
    def __init__(self, *, fetchone_results=None, fetchall_results=None):
        self._fetchone_results = list(fetchone_results or [])
        self._fetchall_results = list(fetchall_results or [])
        self.executed = []
        self.rowcount = 0

    def execute(self, query, params=None):
        self.executed.append((" ".join(query.split()), params))
        self.rowcount = 1

    def fetchone(self):
        return self._fetchone_results.pop(0) if self._fetchone_results else None

    def fetchall(self):
        return self._fetchall_results.pop(0) if self._fetchall_results else []


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor


def fake_get_db(*connections):
    queue = list(connections)

    @contextmanager
    def _get_db():
        if not queue:
            raise AssertionError("No fake database connection left for test")
        yield queue.pop(0)

    return _get_db


def test_sleep_simulation_pipeline(client, api_key, monkeypatch):
    import src.modules.sleep as sleep

    base_time = datetime(2026, 4, 1, 3, 0, 0, tzinfo=timezone.utc)
    rows = [
        {
            "accel_magnitude": 0.01,
            "notification_count": 0,
            "charging": True,
            "hour": (base_time.minute + minute) // 60 + base_time.hour,
            "minute": (base_time.minute + minute) % 60,
        }
        for minute in range(6)
    ]
    insert_cursor = FakeCursor(fetchone_results=[{"id": 99}], fetchall_results=[rows])
    update_cursor = FakeCursor()

    monkeypatch.setattr(
        sleep,
        "get_db",
        fake_get_db(FakeConnection(insert_cursor), FakeConnection(update_cursor)),
    )
    monkeypatch.setattr(sleep, "predict", lambda feature_vector: 0.84)
    monkeypatch.setattr(
        sleep,
        "process_log",
        lambda device_id, timestamp, sleep_prob: {
            "state": "CONFIRMED",
            "sleep_prob": sleep_prob,
            "device_id": device_id,
            "timestamp": timestamp,
        },
    )

    response = client.post(
        "/logs/raw.log",
        headers={"X-API-Key": api_key},
        json={
            "device_id": "pytest_sim_device",
            "timestamp": base_time.isoformat(),
            "charging": True,
            "battery_level": 87,
            "accel_x": 0.01,
            "accel_y": 0.02,
            "accel_z": 0.03,
            "notification_count": 0,
        },
    )

    assert response.status_code == 200
    assert response.json()["state"] == "CONFIRMED"
    assert response.json()["sleep_prob"] == pytest.approx(0.84)
    assert insert_cursor.executed[0][1][1].endswith("+00:00")


def test_logs_require_complete_payload(client, api_key):
    response = client.post(
        "/logs/raw.log",
        headers={"X-API-Key": api_key},
        json={
            "device_id": "pytest_sim_device",
            "timestamp": "2026-04-01T03:00:00Z",
            "charging": True,
            "battery_level": 87,
            "accel_x": 0.01,
            "accel_y": 0.02,
            "notification_count": 0,
        },
    )

    assert response.status_code == 422
    assert "accel_z" in response.text


def test_logs_reject_empty_accelerometer_array(client, api_key):
    response = client.post(
        "/logs/raw.log",
        headers={"X-API-Key": api_key},
        json={
            "device_id": "pytest_sim_device",
            "timestamp": "2026-04-01T03:00:00Z",
            "charging": True,
            "battery_level": 87,
            "accelerometer": [],
            "notification_count": 0,
        },
    )

    assert response.status_code == 422
    assert "accelerometer must contain exactly three values" in response.text


def test_logs_reject_out_of_range_accelerometer_values(client, api_key):
    response = client.post(
        "/logs/raw.log",
        headers={"X-API-Key": api_key},
        json={
            "device_id": "pytest_sim_device",
            "timestamp": "2026-04-01T03:00:00Z",
            "charging": True,
            "battery_level": 87,
            "accel_x": 101,
            "accel_y": 0.02,
            "accel_z": 0.03,
            "notification_count": 0,
        },
    )

    assert response.status_code == 422
    assert "accel_x must be between -100 and 100" in response.text

def test_get_alarm_from_registry():
    device_id = "test_device_1"
    expected_alarm = "2023-10-27T07:00:00Z"

    # Setup state
    alarms.alarm_registry[device_id] = expected_alarm

    # Test
    result = alarms.get_alarm(device_id)

    # Assert
    assert result == expected_alarm

    # Cleanup
    alarms.alarm_registry.pop(device_id, None)

def test_get_alarm_from_db_found(monkeypatch):
    device_id = "test_device_2"
    expected_alarm = "2023-10-28T07:00:00Z"

    # Setup mock db
    cursor = FakeCursor(fetchone_results=[{"alarm_time": expected_alarm}])
    monkeypatch.setattr(
        alarms,
        "get_db",
        fake_get_db(FakeConnection(cursor))
    )

    # Ensure it's not in registry
    alarms.alarm_registry.pop(device_id, None)

    # Test
    result = alarms.get_alarm(device_id)

    # Assert
    assert result == expected_alarm
    assert alarms.alarm_registry.get(device_id) == expected_alarm # Check if it caches

    # Cleanup
    alarms.alarm_registry.pop(device_id, None)

def test_get_alarm_from_db_not_found(monkeypatch):
    device_id = "test_device_3"

    # Setup mock db
    cursor = FakeCursor(fetchone_results=[None])
    monkeypatch.setattr(
        alarms,
        "get_db",
        fake_get_db(FakeConnection(cursor))
    )

    # Ensure it's not in registry
    alarms.alarm_registry.pop(device_id, None)

    # Test
    result = alarms.get_alarm(device_id)

    # Assert
    assert result is None
