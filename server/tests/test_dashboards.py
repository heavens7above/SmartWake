from contextlib import contextmanager

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

def fake_get_db(*connections):
    queue = list(connections)

    @contextmanager
    def _get_db():
        if not queue:
            raise AssertionError("No fake database connection left for test")
        yield queue.pop(0)

    return _get_db

def test_get_dashboard_success(client, api_key, monkeypatch):
    import main
    from src.modules import dashboards

    session_data = {"id": 1, "device_id": "test_device", "quality_rating": None}
    log_data = [{"timestamp": "2024-01-01T00:00:00Z", "sleep_prob": 0.9, "accel_magnitude": 0.0, "charging": True}]

    cursor = FakeCursor(fetchone_results=[session_data], fetchall_results=[log_data])
    monkeypatch.setattr(dashboards, "get_db", fake_get_db(FakeConnection(cursor)))

    response = client.get("/dashboard?device_id=test_device", headers={"X-API-Key": api_key})

    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == "test_device"
    assert data["recent_session"] == session_data
    assert data["logs"] == log_data
    assert len(cursor.executed) == 2

def test_get_dashboard_empty_data(client, api_key, monkeypatch):
    import main
    from src.modules import dashboards

    cursor = FakeCursor(fetchone_results=[None], fetchall_results=[[]])
    monkeypatch.setattr(dashboards, "get_db", fake_get_db(FakeConnection(cursor)))

    response = client.get("/dashboard?device_id=test_device", headers={"X-API-Key": api_key})

    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == "test_device"
    assert data["recent_session"] is None
    assert data["logs"] == []

def test_get_dashboard_invalid_device_id(client, api_key):
    response = client.get("/dashboard?device_id=   ", headers={"X-API-Key": api_key})
    assert response.status_code == 422
    assert "device_id must not be blank" in response.text

def test_submit_rating_success(client, api_key, monkeypatch):
    import main
    from src.modules import dashboards

    cursor = FakeCursor(rowcount=1)
    monkeypatch.setattr(dashboards, "get_db", fake_get_db(FakeConnection(cursor)))

    response = client.post(
        "/rating",
        headers={"X-API-Key": api_key},
        json={"device_id": "test_device", "quality_rating": 4}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert len(cursor.executed) == 1

def test_submit_rating_not_found(client, api_key, monkeypatch):
    import main
    from src.modules import dashboards

    cursor = FakeCursor(rowcount=0) # Simulate no rows updated
    monkeypatch.setattr(dashboards, "get_db", fake_get_db(FakeConnection(cursor)))

    response = client.post(
        "/rating",
        headers={"X-API-Key": api_key},
        json={"device_id": "test_device", "quality_rating": 4}
    )

    assert response.status_code == 404
    assert "No session found" in response.text

def test_submit_rating_invalid_rating(client, api_key):
    response = client.post(
        "/rating",
        headers={"X-API-Key": api_key},
        json={"device_id": "test_device", "quality_rating": 6} # Out of range 1-5
    )
    assert response.status_code == 422
