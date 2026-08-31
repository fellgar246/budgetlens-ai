from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any
from uuid import UUID

from budgetlens.domain.enums import AiRunStatus, MessageRole, ToolExecutionStatus
from budgetlens.domain.errors import ValidationError, field_issue

MAX_MESSAGE_CHARS = 2000


def normalize_message(content: str) -> str:
    cleaned = content.strip()
    if not cleaned:
        raise ValidationError(
            "INVALID_MESSAGE",
            "El mensaje no puede estar vacío.",
            field_errors=[field_issue("content", "INVALID_MESSAGE", "Escribe una pregunta.")],
        )
    if len(cleaned) > MAX_MESSAGE_CHARS:
        raise ValidationError(
            "INVALID_MESSAGE",
            "El mensaje excede el límite permitido.",
            field_errors=[
                field_issue(
                    "content",
                    "INVALID_MESSAGE",
                    f"El mensaje no puede superar {MAX_MESSAGE_CHARS} caracteres.",
                )
            ],
        )
    return cleaned


@dataclass(frozen=True, slots=True)
class Conversation:
    id: UUID
    organization_id: UUID
    user_id: UUID
    title: str
    context_filters: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self, *, now: datetime) -> Conversation:
        if self.deleted_at is not None:
            return self
        return replace(self, deleted_at=now, updated_at=now)


@dataclass(frozen=True, slots=True)
class ConversationMessage:
    id: UUID
    organization_id: UUID
    conversation_id: UUID
    role: MessageRole
    content: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AiRun:
    id: UUID
    organization_id: UUID
    conversation_id: UUID
    provider: str
    model_id: str
    latency_ms: int
    input_units: int
    output_units: int
    status: AiRunStatus
    trace_id: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ToolExecution:
    id: UUID
    organization_id: UUID
    ai_run_id: UUID
    tool_name: str
    argument_hash: str
    result_hash: str
    row_count: int
    duration_ms: int
    status: ToolExecutionStatus
