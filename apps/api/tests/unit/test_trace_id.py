from __future__ import annotations

from fastapi.testclient import TestClient

from budgetlens.presentation.middleware import parse_traceparent


def test_generated_trace_id_is_returned(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")
    trace_id = response.headers["x-trace-id"]
    assert len(trace_id) >= 8


def test_incoming_trace_id_is_preserved(client: TestClient) -> None:
    response = client.get("/api/v1/health/live", headers={"X-Trace-Id": "client-trace-001"})
    assert response.headers["x-trace-id"] == "client-trace-001"


def test_valid_traceparent_is_used(client: TestClient) -> None:
    response = client.get(
        "/api/v1/health/live",
        headers={"traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"},
    )
    assert response.headers["x-trace-id"] == "0af7651916cd43dd8448eb211c80319c"


def test_parse_traceparent_rejects_invalid() -> None:
    assert parse_traceparent("not-a-trace") is None
    assert parse_traceparent(None) is None
