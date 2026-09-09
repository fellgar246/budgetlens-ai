from __future__ import annotations

from fastapi.testclient import TestClient

from budgetlens.cli import run_worker_loop
from budgetlens.runtime import mark_shutting_down


def test_mutating_requests_are_rejected_during_shutdown(client: TestClient) -> None:
    mark_shutting_down()
    response = client.post(
        "/api/v1/organizations",
        headers={"Authorization": "Bearer 11111111-1111-4111-8111-111111111111"},
        json={"name": "Gamma", "slug": "gamma", "functional_currency": "MXN"},
    )
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "SHUTTING_DOWN"
    assert body["error"]["retryable"] is True
    assert body["trace_id"]
    assert body["trace_id"] != "shutdown"
    assert response.headers["x-trace-id"] == body["trace_id"]
    live = client.get("/api/v1/health/live")
    assert live.status_code == 200


def test_worker_loop_stops_after_one_tick() -> None:
    ticks: list[int] = []
    stop = {"value": False}

    def tick() -> int:
        ticks.append(1)
        stop["value"] = True
        return 0

    run_worker_loop(
        poll_seconds=0.2,
        should_stop=lambda: stop["value"],
        sleeper=lambda _: None,
        on_tick=tick,
    )
    assert ticks == [1]
