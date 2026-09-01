from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from budgetlens.config import Settings
from budgetlens.domain.conversation import ConversationMessage


@dataclass(frozen=True, slots=True)
class ToolRequest:
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ProviderResult:
    text: str | None
    tool_requests: tuple[ToolRequest, ...]
    input_units: int
    output_units: int
    model_id: str


class AIProvider(Protocol):
    def complete(
        self,
        *,
        messages: list[ConversationMessage],
        question: str,
        settings: Settings,
    ) -> ProviderResult: ...
