from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AuditEvent:
    id: UUID
    organization_id: UUID | None
    actor_id: UUID
    action: str
    resource_type: str
    resource_id: UUID
    outcome: str
    metadata: dict[str, Any]
    trace_id: str
    created_at: datetime
    schema_version: int = 1


def sanitized_metadata(values: dict[str, Any]) -> dict[str, Any]:
    blocked = {
        "password",
        "token",
        "secret",
        "authorization",
        "database_url",
        "prompt",
        "content",
        "amount",
        "download_url",
        "presigned",
    }
    return {key: value for key, value in values.items() if key.lower() not in blocked}
