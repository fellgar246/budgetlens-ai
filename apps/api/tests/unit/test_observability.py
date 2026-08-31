from __future__ import annotations

import json
import logging

from budgetlens.logging import JsonLogFormatter
from budgetlens.observability import (
    classify_failure,
    hash_identifier,
    metrics_registry,
    reset_metrics,
    sanitize_log_payload,
)


def test_sanitize_log_payload_drops_secrets_and_financial_fields() -> None:
    payload = {
        "event": "http.request.completed",
        "trace_id": "abc12345",
        "token": "super-secret",
        "database_url": "postgresql://budgetlens:budgetlens_local_only@localhost/budgetlens",
        "amount": "1234.0000",
        "prompt": "explica el gasto de operaciones",
        "organization_id_hash": "deadbeef",
    }
    cleaned = sanitize_log_payload(payload)
    serialized = json.dumps(cleaned)
    assert "super-secret" not in serialized
    assert "budgetlens_local_only" not in serialized
    assert "1234.0000" not in serialized
    assert "explica el gasto" not in serialized
    assert cleaned["event"] == "http.request.completed"
    assert cleaned["organization_id_hash"] == "deadbeef"


def test_json_formatter_omits_blocked_record_attributes() -> None:
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        "budgetlens.http",
        logging.INFO,
        __file__,
        1,
        "http.request.completed",
        (),
        None,
    )
    record.event = "http.request.completed"
    record.trace_id = "trace-001"
    record.token = "should-not-appear"
    record.amount = "99.0000"
    rendered = formatter.format(record)
    assert "should-not-appear" not in rendered
    assert "99.0000" not in rendered
    assert "trace-001" in rendered


def test_identifier_hash_is_stable_and_short() -> None:
    hashed = hash_identifier("11111111-1111-4111-8111-111111111111")
    assert hashed == hash_identifier("11111111-1111-4111-8111-111111111111")
    assert hashed is not None
    assert len(hashed) == 16
    assert hashed != "11111111-1111-4111-8111-111111111111"


def test_failure_classes_distinguish_sources() -> None:
    assert classify_failure(status_code=500) == "application"
    assert classify_failure(dependency="database") == "dependency"
    assert classify_failure() == "infrastructure"


def test_metrics_snapshot_has_no_tenant_labels() -> None:
    reset_metrics()
    metrics_registry().record_request(
        method="GET",
        route="/api/v1/analytics/variance-summary",
        status_code=200,
        duration_ms=12,
    )
    snapshot = metrics_registry().snapshot()
    serialized = json.dumps(snapshot)
    assert "11111111" not in serialized
    assert snapshot["requests"][0]["route"] == "/api/v1/analytics/variance-summary"
    reset_metrics()
