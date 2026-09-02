#!/usr/bin/env python3
"""Fail unexpected Terraform destroys and write a secret-free plan summary."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

CRITICAL_DESTROY_TYPES = frozenset(
    {
        "aws_db_instance",
        "aws_s3_bucket",
        "aws_kms_key",
        "aws_cognito_user_pool",
        "aws_ecr_repository",
        "aws_cloudfront_distribution",
        "aws_ecs_cluster",
        "aws_iam_role",
    }
)
SECRET_KEY_FRAGMENTS = (
    "password",
    "secret",
    "token",
    "private_key",
    "access_key",
    "database_url",
    "pepper",
)
SECRET_VALUE_RE = re.compile(
    r"AKIA[0-9A-Z]{16}|BEGIN (RSA |OPENSSH )?PRIVATE KEY|postgres(?:ql)?(?:\+psycopg)?://\S+",
    re.I,
)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def parse_plan(raw: Mapping[str, Any]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for item in raw.get("resource_changes") or []:
        if not isinstance(item, dict):
            continue
        change = _as_dict(item.get("change"))
        actions = [str(action) for action in change.get("actions") or []]
        if not actions or actions == ["no-op"]:
            continue
        changes.append(
            {
                "address": str(item.get("address") or ""),
                "type": str(item.get("type") or ""),
                "actions": actions,
            }
        )
    return changes


def unexpected_destroys(
    changes: Iterable[Mapping[str, Any]],
    allowed: Iterable[str] = (),
) -> list[str]:
    allow = {item.strip() for item in allowed if item.strip()}
    offenders: list[str] = []
    for change in changes:
        actions = list(change.get("actions") or [])
        address = str(change.get("address") or "")
        resource_type = str(change.get("type") or "")
        if address in allow:
            continue
        destroy_only = actions == ["delete"]
        critical_replace = "delete" in actions and resource_type in CRITICAL_DESTROY_TYPES
        if destroy_only or critical_replace:
            offenders.append(f"{address} ({','.join(actions)})")
    return offenders


def _looks_secret(key: str, value: Any) -> bool:
    lowered = key.lower()
    if any(fragment in lowered for fragment in SECRET_KEY_FRAGMENTS):
        return True
    if isinstance(value, str) and SECRET_VALUE_RE.search(value):
        return True
    return False


def redact(value: Any, key: str = "") -> Any:
    if _looks_secret(key, value):
        return "(redacted)"
    if isinstance(value, dict):
        return {str(child): redact(child_value, str(child)) for child, child_value in value.items()}
    if isinstance(value, list):
        return [redact(item, key) for item in value]
    if isinstance(value, str) and SECRET_VALUE_RE.search(value):
        return "(redacted)"
    return value


def summarize(changes: Sequence[Mapping[str, Any]]) -> str:
    if not changes:
        return "No resource changes."
    lines = ["| Address | Actions |", "|---|---|"]
    for change in changes:
        actions = ", ".join(str(action) for action in change.get("actions") or [])
        lines.append(f"| `{change.get('address')}` | {actions} |")
    return "\n".join(lines) + "\n"


def load_plan(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Terraform plan JSON must be an object.")
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_json", type=Path)
    parser.add_argument("--summary", type=Path)
    parser.add_argument(
        "--allow-destroy",
        default=os.environ.get("ALLOW_DESTROYS", ""),
        help="Comma-separated resource addresses that may be destroyed.",
    )
    args = parser.parse_args(argv)

    plan = load_plan(args.plan_json)
    changes = parse_plan(plan)
    allowed = [item.strip() for item in str(args.allow_destroy).split(",")]
    offenders = unexpected_destroys(changes, allowed)
    summary = summarize(changes)
    if args.summary:
        args.summary.write_text(summary, encoding="utf-8")
    sys.stdout.write(summary)
    if offenders:
        sys.stderr.write("Unexpected destroys:\n" + "\n".join(offenders) + "\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
