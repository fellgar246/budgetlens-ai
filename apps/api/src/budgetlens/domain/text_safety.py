from __future__ import annotations

import re
from pathlib import Path

_INJECTION_PREFIXES = ("=", "+", "-", "@")
_UNSAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")
_DECIMAL_TEXT = re.compile(r"^-?\d+(?:\.\d+)?$")


def neutralize_csv_text(value: str) -> str:
    if _DECIMAL_TEXT.fullmatch(value):
        return value
    if value.startswith(_INJECTION_PREFIXES):
        return f"'{value}"
    return value


def sanitize_filename(value: str) -> str:
    cleaned = _UNSAFE_FILENAME.sub("_", Path(value).name).strip("._")
    if not cleaned or cleaned in {".", ".."}:
        return "upload.bin"
    return cleaned[:180]


def redact_cell(value: str, *, limit: int = 40) -> str:
    cleaned = value.strip()
    if not cleaned:
        return ""
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 1]}…"
