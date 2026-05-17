import pytest


def test_health_endpoint(http_client):
    response = http_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db":
        "connected"}