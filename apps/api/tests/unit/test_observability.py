from __future__ import annotations

import json
import logging

from budgetlens.logging import JsonLogFormatter
from budgetlens.observability import (
    classify_failure,
    hash_identifier,
    logical_query_name,
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
    assert "50" in snapshot["request_duration_histogram"]
    reset_metrics()


def test_logical_query_name_never_includes_sql_or_params() -> None:
    named_explicit = logical_query_name(
        "SELECT * FROM users WHERE id = '11111111'",
        query_name="users.list",
    )
    assert named_explicit == "users.list"
    named = logical_query_name("SELECT amount FROM financial_entries WHERE amount = 99.0000")
    assert named == "sql.select"
    assert "amount" not in named
    assert "99.0000" not in named
    assert "financial_entries" not in named


def test_metrics_cover_import_ai_and_safe_error_codes() -> None:
    reset_metrics()
    registry = metrics_registry()
    registry.record_job_status(
        "validated",
        job_type="budget",
        phase="validation",
        duration_ms=40,
        rows_processed=10,
        rows_error=2,
        bytes_processed=2048,
    )
    registry.record_ai_run(
        latency_ms=80,
        input_units=12,
        output_units=4,
        tool_calls=2,
        tool_failures=1,
        grounding_failed=True,
    )
    registry.record_error_code("PERMISSION_DENIED")
    registry.record_error_code("not-a-safe-code")
    registry.record_query("sql.select", 3)
    snapshot = registry.snapshot(input_unit_cost_micros=100, output_unit_cost_micros=200)
    assert snapshot["jobs"]["by_type"] == {"budget": 1}
    assert snapshot["jobs"]["rows_processed"] == 10
    assert snapshot["jobs"]["rows_error"] == 2
    assert snapshot["jobs"]["error_ratio"] == 0.2
    assert snapshot["jobs"]["bytes_processed"] == 2048
    assert snapshot["ai"]["grounding_failures"] == 1
    assert snapshot["ai"]["input_units"] == 12
    assert snapshot["ai"]["output_units"] == 4
    assert snapshot["ai"]["estimated_cost"]["estimate"] is True
    assert snapshot["ai"]["circuit_open"] == 0
    assert snapshot["error_codes"] == {"PERMISSION_DENIED": 1}
    assert snapshot["db_queries"][0]["name"] == "sql.select"
    assert "organization" not in json.dumps(snapshot).lower()
    reset_metrics()
