from __future__ import annotations

import base64
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast
from uuid import UUID

from budgetlens.domain.errors import ValidationError, field_issue

DEFAULT_LIMIT = 50
MAX_LIMIT = 100
ABSOLUTE_MAX_LIMIT = 500

if MAX_LIMIT > ABSOLUTE_MAX_LIMIT:
    raise RuntimeError("Page limit cannot exceed 500 rows.")


@dataclass(frozen=True, slots=True)
class Page[T]:
    items: list[T]
    next_cursor: str | None
    has_more: bool


def clamp_limit(limit: int | None) -> int:
    value = DEFAULT_LIMIT if limit is None else limit
    if value < 1 or value > MAX_LIMIT:
        raise ValidationError(
            "INVALID_LIMIT",
            "El límite de página debe estar entre 1 y 100.",
            field_errors=[
                field_issue("limit", "INVALID_LIMIT", "El límite debe estar entre 1 y 100.")
            ],
        )
    return value


def offset_page[T](items: Sequence[T], *, cursor: str | None, limit: int | None) -> Page[T]:
    page_limit = clamp_limit(limit)
    offset = 0
    parsed = decode_cursor(cursor)
    if parsed is not None:
        raw = parsed.get("offset", "0")
        try:
            offset = max(0, int(raw))
        except ValueError as exc:
            raise ValidationError(
                "INVALID_CURSOR",
                "El cursor de paginación no es válido.",
                field_errors=[
                    field_issue("cursor", "INVALID_CURSOR", "El cursor de paginación no es válido.")
                ],
            ) from exc
    window = list(items[offset : offset + page_limit + 1])
    has_more = len(window) > page_limit
    page_items = window[:page_limit]
    next_cursor = encode_cursor({"offset": str(offset + page_limit)}) if has_more else None
    return Page(items=page_items, next_cursor=next_cursor, has_more=has_more)


def encode_cursor(payload: dict[str, str]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(value: str | None) -> dict[str, str] | None:
    if value is None or value == "":
        return None
    padding = "=" * (-len(value) % 4)
    try:
        decoded = base64.urlsafe_b64decode(value + padding)
        payload = json.loads(decoded.decode("utf-8"))
    except Exception as exc:
        raise ValidationError(
            "INVALID_CURSOR",
            "El cursor de paginación no es válido.",
            field_errors=[
                field_issue("cursor", "INVALID_CURSOR", "El cursor de paginación no es válido.")
            ],
        ) from exc
    if not isinstance(payload, dict):
        raise ValidationError(
            "INVALID_CURSOR",
            "El cursor de paginación no es válido.",
            field_errors=[
                field_issue("cursor", "INVALID_CURSOR", "El cursor de paginación no es válido.")
            ],
        )
    typed = cast(dict[object, object], payload)
    return {str(key): str(item) for key, item in typed.items()}


def parse_uuid(value: str, *, field: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise ValidationError(
            "INVALID_ID",
            "El identificador no es válido.",
            field_errors=[field_issue(field, "INVALID_ID", "El identificador no es válido.")],
        ) from exc
