from fastapi.testclient import TestClient

def test_cors_headers(client):
    response = client.options("/health", headers={
        "Origin": "http://evil.com",
        "Access-Control-Request-Method": "GET"
    })

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    assert response.headers.get("access-control-allow-credentials") != "true"
