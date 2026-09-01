from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from budgetlens.domain.audit import AuditEvent, sanitized_metadata
from budgetlens.presentation.schemas_ops import audit_event_response


def test_sanitized_metadata_drops_sensitive_keys() -> None:
    cleaned = sanitized_metadata(
        {
            "status": "published",
            "token": "secret-token",
            "amount": "100.0000",
            "download_url": "https://example.invalid/file",
            "prompt": "full question",
        }
    )
    assert cleaned == {"status": "published"}


def test_audit_event_response_omits_sensitive_metadata() -> None:
    event = AuditEvent(
        id=UUID(int=1),
        organization_id=UUID(int=2),
        actor_id=UUID(int=3),
        action="export.created",
        resource_type="export_job",
        resource_id=UUID(int=4),
        outcome="success",
        metadata={"filename": "ok.csv", "download_url": "https://example.invalid/tmp"},
        trace_id="trace-1",
        created_at=datetime(2026, 8, 31, tzinfo=UTC),
    )
    payload = audit_event_response(event)
    assert payload.metadata == {"filename": "ok.csv"}
    assert "download_url" not in payload.metadata
