#!/usr/bin/env python3
"""Record post-deploy observation evidence without secrets."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

OBSERVATION_ITEMS: tuple[dict[str, str], ...] = (
    {"id": "api_5xx_latency", "summary": "API 5xx and latency"},
    {"id": "healthy_tasks_restarts", "summary": "Healthy tasks and restarts"},
    {"id": "db_connections_storage", "summary": "Database connections and storage"},
    {"id": "bedrock_errors_throttling", "summary": "Bedrock errors and throttling"},
    {"id": "import_failures", "summary": "Import failures"},
    {"id": "spend_and_logs", "summary": "Spend and ingested logs"},
)
FORBIDDEN_KEYS = frozenset(
    {
        "password",
        "token",
        "secret",
        "database_url",
        "prompt",
        "amount",
        "cells",
    }
)


def render_checklist() -> str:
    lines = [
        "# Post-deploy observation",
        "",
        "Watch the agreed window. Record evidence without secrets or financial rows.",
        "",
    ]
    for item in OBSERVATION_ITEMS:
        lines.append(f"- [ ] {item['summary']}")
    lines.append("")
    return "\n".join(lines)


def reject_forbidden(notes: Mapping[str, Any]) -> None:
    for key, value in notes.items():
        if key.lower() in FORBIDDEN_KEYS:
            raise ValueError(f"{key} must not be recorded in observation evidence")
        text = str(value)
        if "AKIA" in text or "postgresql://" in text or "Bearer " in text:
            raise ValueError("observation notes look like a secret")


def build_observation(
    *,
    environment: str,
    recorded_by: str,
    window: str,
    notes: Mapping[str, Any] | None = None,
    recorded_at: str | None = None,
) -> dict[str, Any]:
    if not recorded_by.strip() or recorded_by.strip().lower() in {"agent", "auto", "default"}:
        raise ValueError("observation requires a human recorded_by")
    payload = dict(notes or {})
    reject_forbidden(payload)
    return {
        "environment": environment,
        "recorded_by": recorded_by.strip(),
        "recorded_at": recorded_at or datetime.now(UTC).date().isoformat(),
        "window": window,
        "items": [item["id"] for item in OBSERVATION_ITEMS],
        "notes": payload,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-checklist", action="store_true")
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--environment", default="dev")
    parser.add_argument("--recorded-by", default="")
    parser.add_argument("--window", default="agreed post-deploy window")
    parser.add_argument("--note", action="append", default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    if args.print_checklist:
        print(render_checklist(), end="")
        if not args.record:
            return 0
    if not args.record:
        parser.error("use --print-checklist and/or --record")
    notes: dict[str, str] = {}
    for raw in args.note:
        key, separator, value = raw.partition("=")
        if not separator:
            raise SystemExit("notes must be key=value")
        notes[key] = value
    record = build_observation(
        environment=args.environment,
        recorded_by=args.recorded_by,
        window=args.window,
        notes=notes,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        args.output.with_suffix(".md").write_text(render_checklist(), encoding="utf-8")
        print(args.output)
    else:
        print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
