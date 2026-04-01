def test_server_online(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "SmartWake Sleep Intelligence Server",
        "base_url": "https://smartwake.test",
    }


def test_authentication_rejects_invalid_key(client):
    response = client.get(
        "/dashboard",
        headers={"X-API-Key": "invalid-key"},
        params={"device_id": "pytest-device"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Could not validate API KEY"
