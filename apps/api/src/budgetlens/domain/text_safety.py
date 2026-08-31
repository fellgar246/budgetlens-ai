from __future__ import annotations

_INJECTION_PREFIXES = ("=", "+", "-", "@")


def neutralize_csv_text(value: str) -> str:
    if value.startswith(_INJECTION_PREFIXES):
        return f"'{value}"
    return value


def redact_cell(value: str, *, limit: int = 40) -> str:
    cleaned = value.strip()
    if not cleaned:
        return ""
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 1]}…"
