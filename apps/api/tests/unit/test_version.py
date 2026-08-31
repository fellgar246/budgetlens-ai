from __future__ import annotations

from fastapi.testclient import TestClient


def test_version_returns_safe_build_fields(client: TestClient) -> None:
    response = client.get("/api/v1/version")
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "version": "0.1.0",
        "commit": "testsha",
        "build_time": "2026-08-31T00:00:00Z",
    }
    assert "DATABASE_URL" not in response.text
