from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

AuditOutcome = Literal["success", "denied", "failed"]
AuditActorType = Literal["user", "system"]

AUDIT_SCHEMA_VERSION = 1
AUDIT_SCHEMA_VERSION_LABEL = "1.0"

ACTOR_USER: AuditActorType = "user"
ACTOR_SYSTEM: AuditActorType = "system"

SYSTEM_AUTH = "auth"
SYSTEM_WATCHDOG = "watchdog"
SYSTEM_SEED = "seed"

AUTH_LOGIN_SUCCEEDED = "auth.login_succeeded"
AUTH_LOGIN_FAILED = "auth.login_failed"
ORGANIZATION_CREATED = "organization.created"
ORGANIZATION_UPDATED = "organization.updated"
ORGANIZATION_ARCHIVED = "organization.archived"
MEMBERSHIP_CREATED = "membership.created"
MEMBERSHIP_ROLE_CHANGED = "membership.role_changed"
MEMBERSHIP_DISABLED = "membership.disabled"
DIMENSION_CREATED = "dimension.created"
DIMENSION_UPDATED = "dimension.updated"
DIMENSION_ARCHIVED = "dimension.archived"
BUDGET_VERSION_CREATED = "budget_version.created"
BUDGET_VERSION_PUBLISHED = "budget_version.published"
BUDGET_VERSION_ACTIVATED = "budget_version.activated"
BUDGET_VERSION_ARCHIVED = "budget_version.archived"
IMPORT_CREATED = "import.created"
IMPORT_VALIDATED = "import.validated"
IMPORT_COMMITTED = "import.committed"
IMPORT_FAILED = "import.failed"
IMPORT_CANCELLED = "import.cancelled"
EXPORT_CREATED = "export.created"
EXPORT_DOWNLOAD_AUTHORIZED = "export.download_authorized"
SCENARIO_CREATED = "scenario.created"
SCENARIO_UPDATED = "scenario.updated"
SCENARIO_ARCHIVED = "scenario.archived"
AI_MESSAGE_REQUESTED = "ai.message_requested"
AI_TOOL_EXECUTED = "ai.tool_executed"
AI_RESPONSE_COMPLETED = "ai.response_completed"
AI_RESPONSE_FAILED = "ai.response_failed"
AI_GROUNDING_FAILED = "ai.grounding_failed"
CONVERSATION_DELETED = "conversation.deleted"
SECURITY_ACCESS_DENIED = "security.access_denied"
DEMO_SEEDED = "demo.seeded"

_BLOCKED_METADATA = {
    "password",
    "token",
    "secret",
    "authorization",
    "cookie",
    "database_url",
    "prompt",
    "content",
    "amount",
    "cells",
    "download_url",
    "presigned",
}


@dataclass(frozen=True, slots=True)
class AuditEvent:
    id: UUID
    organization_id: UUID | None
    actor_type: str
    actor_id: UUID | None
    actor_ref: str
    action: str
    resource_type: str
    resource_id: UUID
    outcome: str
    metadata: dict[str, Any]
    trace_id: str
    created_at: datetime
    schema_version: int = AUDIT_SCHEMA_VERSION

    def actor_identity(self) -> str:
        if self.actor_ref:
            return self.actor_ref
        if self.actor_id is not None:
            return str(self.actor_id)
        return SYSTEM_AUTH


def sanitized_metadata(values: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in values.items():
        if key.lower() in _BLOCKED_METADATA:
            continue
        cleaned[key] = value
    return cleaned
