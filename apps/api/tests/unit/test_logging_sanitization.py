from __future__ import annotations

import json
import logging

from fastapi.testclient import TestClient

from budgetlens.logging import JsonLogFormatter
from budgetlens.observability import hash_identifier, sanitize_log_payload


def test_sanitize_log_payload_drops_secrets_and_financial_fields() -> None:
    payload = {
        "event": "http.request.completed",
        "trace_id": "abc12345",
        "token": "super-secret",
        "database_url": "postgresql://budgetlens:budgetlens_local_only@localhost/budgetlens",
        "prompt": "explica el exceso de gasto",
        "amount": "12500.0000",
        "organization_id_hash": "abcd",
    }
    cleaned = sanitize_log_payload(payload)
    rendered = json.dumps(cleaned)
    assert "super-secret" not in rendered
    assert "postgresql://" not in rendered
    assert "exceso de gasto" not in rendered
    assert "12500.0000" not in rendered
    assert cleaned["event"] == "http.request.completed"
    assert cleaned["organization_id_hash"] == "abcd"


def test_json_formatter_omits_blocked_record_attributes() -> None:
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="budgetlens.http",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="http.request.completed",
        args=(),
        exc_info=None,
    )
    record.event = "http.request.completed"
    record.trace_id = "trace-001"
    record.token = "should-not-appear"
    record.prompt = "pregunta financiera completa"
    rendered = formatter.format(record)
    assert "should-not-appear" not in rendered
    assert "pregunta financiera" not in rendered
    assert "trace-001" in rendered


def test_http_logs_omit_forbidden_values(client: TestClient) -> None:
    captured: list[str] = []

    class _Handler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(JsonLogFormatter().format(record))

    handler = _Handler()
    logger = logging.getLogger("budgetlens.http")
    original_level = logger.level
    original_disabled = logger.disabled
    logger.setLevel(logging.INFO)
    logger.disabled = False
    logger.addHandler(handler)
    try:
        response = client.get(
            "/api/v1/health/live",
            headers={
                "Authorization": "Bearer super-secret-token-value",
                "Cookie": "session=cookie-secret",
                "X-Organization-Id": "11111111-1111-4111-8111-111111111111",
                "X-Trace-Id": "trace-log-001",
            },
        )
    finally:
        logger.removeHandler(handler)
        logger.setLevel(original_level)
        logger.disabled = original_disabled
    assert response.status_code == 200
    assert response.headers["x-trace-id"] == "trace-log-001"
    assert captured
    blob = "\n".join(captured)
    assert "super-secret-token-value" not in blob
    assert "cookie-secret" not in blob
    assert "postgresql://" not in blob
    assert "DATABASE_URL" not in blob
    assert "11111111-1111-4111-8111-111111111111" not in blob
    payload = json.loads(captured[-1])
    assert payload["event"] == "http.request.completed"
    assert payload["trace_id"] == "trace-log-001"
    assert payload["organization_id_hash"]
    assert payload["organization_id_hash"] != "11111111-1111-4111-8111-111111111111"


def test_identifier_hash_is_stable_and_truncated() -> None:
    first = hash_identifier("11111111-1111-4111-8111-111111111111")
    second = hash_identifier("11111111-1111-4111-8111-111111111111")
    assert first == second
    assert first is not None
    assert len(first) == 16
    assert first != "11111111-1111-4111-8111-111111111111"
