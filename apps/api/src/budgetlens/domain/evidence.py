from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from budgetlens.domain.money import Currency, MoneyAmount

EVIDENCE_ID_RE = re.compile(r"\bev_(\d+)\b")
DECIMAL_RE = re.compile(r"(?<![A-Za-z0-9.])-?\d+(?:\.\d{1,6})?(?![0-9])")
YEAR_RE = re.compile(r"^20\d{2}$")
GROUNDING_FAILED_MESSAGE = "No pude verificar la respuesta"


@dataclass(frozen=True, slots=True)
class Evidence:
    tool_name: str
    authorized: bool
    period_from: date
    period_to: date
    budget_version_id: UUID
    currency: Currency
    figures: tuple[MoneyAmount, ...]


@dataclass(frozen=True, slots=True)
class GroundingDecision:
    can_conclude: bool
    period_from: date | None
    period_to: date | None
    budget_version_id: UUID | None
    currency: Currency | None


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    id: str
    tool: str
    label: str
    data: dict[str, Any]
    figures: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GroundingCheck:
    ok: bool
    failed: bool
    missing_citations: tuple[str, ...]
    unknown_figures: tuple[str, ...]


def evaluate_grounding(evidence: Sequence[Evidence]) -> GroundingDecision:
    if not evidence or not all(item.authorized and item.figures for item in evidence):
        return GroundingDecision(
            can_conclude=False,
            period_from=None,
            period_to=None,
            budget_version_id=None,
            currency=None,
        )
    first = evidence[0]
    return GroundingDecision(
        can_conclude=True,
        period_from=first.period_from,
        period_to=first.period_to,
        budget_version_id=first.budget_version_id,
        currency=first.currency,
    )


def conversation_may_mutate() -> bool:
    return False


def dimension_label_as_data(value: str) -> str:
    return value


def extract_amounts(payload: Mapping[str, Any] | Sequence[object] | object) -> list[MoneyAmount]:
    found: list[MoneyAmount] = []

    def walk(value: object) -> None:
        if isinstance(value, dict):
            for key, item in cast(dict[str, object], value).items():
                if str(key).endswith("_amount") and isinstance(item, str):
                    found.append(MoneyAmount(item))
                else:
                    walk(item)
        elif isinstance(value, list):
            for item in cast(list[object], value):
                walk(item)

    walk(payload)
    return found


def evidence_figure_map(records: Sequence[EvidenceRecord]) -> dict[str, EvidenceRecord]:
    return {item.id: item for item in records}


def cited_evidence_ids(text: str) -> tuple[str, ...]:
    return tuple(f"ev_{match}" for match in EVIDENCE_ID_RE.findall(text))


def extract_decimal_literals(text: str) -> tuple[str, ...]:
    found: list[str] = []
    for raw in DECIMAL_RE.findall(text):
        if YEAR_RE.match(raw):
            continue
        if raw.startswith("ev_"):
            continue
        try:
            parsed = Decimal(raw)
        except Exception:
            continue
        if parsed.copy_abs() < 100 and "." not in raw:
            continue
        found.append(format(parsed, "f"))
    return tuple(found)


def parse_structured_answer(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if not stripped.startswith("{"):
        return None
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    typed = cast(dict[object, object], parsed)
    return {str(key): item for key, item in typed.items()}


def verify_answer_grounding(answer: str, records: Sequence[EvidenceRecord]) -> GroundingCheck:
    allowed = evidence_figure_map(records)
    cited = cited_evidence_ids(answer)
    missing = tuple(item for item in cited if item not in allowed)
    allowed_figures = {_normalize_figure(figure) for record in records for figure in record.figures}
    unknown: list[str] = []
    for literal in extract_decimal_literals(answer):
        normalized = _normalize_figure(literal)
        if normalized not in allowed_figures:
            unknown.append(literal)
    failed = bool(missing or unknown)
    return GroundingCheck(
        ok=not failed,
        failed=failed,
        missing_citations=missing,
        unknown_figures=tuple(unknown),
    )


def _normalize_figure(value: str) -> str:
    try:
        return MoneyAmount(value).as_text()
    except Exception:
        try:
            return format(Decimal(value), "f")
        except Exception:
            return value
