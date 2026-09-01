from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from budgetlens.domain.audit import (
    ACTOR_SYSTEM,
    ACTOR_USER,
    AUDIT_SCHEMA_VERSION_LABEL,
    SYSTEM_WATCHDOG,
    AuditEvent,
    sanitized_metadata,
)
from budgetlens.presentation.schemas_ops import audit_event_response


def test_sanitized_metadata_drops_sensitive_keys() -> None:
    cleaned = sanitized_metadata(
        {
            "status": "published",
            "token": "secret-token",
            "amount": "100.0000",
            "download_url": "https://example.invalid/file",
            "prompt": "full question",
            "cells": ["raw"],
        }
    )
    assert cleaned == {"status": "published"}


def test_audit_event_response_matches_contract_and_omits_sensitive_metadata() -> None:
    event = AuditEvent(
        id=UUID(int=1),
        organization_id=UUID(int=2),
        actor_type=ACTOR_USER,
        actor_id=UUID(int=3),
        actor_ref=str(UUID(int=3)),
        action="export.created",
        resource_type="export_job",
        resource_id=UUID(int=4),
        outcome="success",
        metadata={"filename": "ok.csv", "download_url": "https://example.invalid/tmp"},
        trace_id="trace-1",
        created_at=datetime(2026, 8, 31, tzinfo=UTC),
    )
    payload = audit_event_response(event)
    assert payload.schema_version == AUDIT_SCHEMA_VERSION_LABEL
    assert payload.event_id == event.id
    assert payload.occurred_at == event.created_at
    assert payload.organization_id == event.organization_id
    assert payload.actor.type == "user"
    assert payload.actor.id == str(UUID(int=3))
    assert payload.resource.type == "export_job"
    assert payload.resource.id == event.resource_id
    assert payload.outcome == "success"
    assert payload.metadata == {"filename": "ok.csv"}
    assert "download_url" not in payload.metadata
    assert payload.id == event.id
    assert payload.actor_id == str(UUID(int=3))


def test_system_actor_uses_service_identity() -> None:
    event = AuditEvent(
        id=UUID(int=5),
        organization_id=UUID(int=2),
        actor_type=ACTOR_SYSTEM,
        actor_id=None,
        actor_ref=SYSTEM_WATCHDOG,
        action="import.failed",
        resource_type="import_job",
        resource_id=UUID(int=6),
        outcome="failed",
        metadata={"failure_code": "JOB_TIMEOUT"},
        trace_id="trace-job",
        created_at=datetime(2026, 9, 1, tzinfo=UTC),
    )
    payload = audit_event_response(event)
    assert payload.actor.type == "system"
    assert payload.actor.id == SYSTEM_WATCHDOG
    assert payload.actor_id == SYSTEM_WATCHDOG
    assert payload.outcome == "failed"
