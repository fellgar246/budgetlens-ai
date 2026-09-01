from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from budgetlens.config import Settings
from budgetlens.domain.conversation import ConversationMessage


@dataclass(frozen=True, slots=True)
class ToolRequest:
    name: str
    arguments: dict[str, Any]
    request_id: str = ""


@dataclass(frozen=True, slots=True)
class ToolResult:
    name: str
    evidence_id: str
    payload: dict[str, Any]
    request_id: str = ""


@dataclass(frozen=True, slots=True)
class ProviderResult:
    text: str | None
    tool_requests: tuple[ToolRequest, ...]
    input_units: int
    output_units: int
    model_id: str
    structured: dict[str, Any] | None = None


class AIProvider(Protocol):
    def complete(
        self,
        *,
        messages: list[ConversationMessage],
        question: str,
        settings: Settings,
        system_prompt: str = "",
        tool_results: tuple[ToolResult, ...] = (),
        timeout_seconds: int | None = None,
    ) -> ProviderResult: ...
