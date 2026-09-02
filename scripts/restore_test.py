#!/usr/bin/env python3
"""Guards for an isolated AWS restore test. Never points production traffic."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from typing import Any

RESTORE_INSTANCE_NAME = "budgetlens-dev-restore"
RESTORE_STEPS: tuple[str, ...] = (
    "Restore the backup onto an isolated resource named budgetlens-dev-restore.",
    "Do not point production or development traffic at the restored resource.",
    "Check schema, row counts, and tenant invariants.",
    "Document the observed RPO and RTO.",
    "Delete the restored resource after authorization and review cost.",
)


def isolated_restore_name(environment: str) -> str:
    if environment != "dev":
        raise ValueError("the isolated restore test uses the development snapshot only")
    return RESTORE_INSTANCE_NAME


def refuse_production_traffic(application_url: str, restore_endpoint: str) -> None:
    app = application_url.strip().rstrip("/")
    restore = restore_endpoint.strip().rstrip("/")
    if not restore:
        raise ValueError("restore endpoint is required")
    if app and restore == app:
        raise ValueError("restored resource must not receive application traffic")
    if "prod" in restore.lower() and "restore" not in restore.lower():
        raise ValueError("restore must not target a production identifier")


def review_restore_facts(facts: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if facts.get("identifier") != RESTORE_INSTANCE_NAME:
        errors.append(f"identifier must be {RESTORE_INSTANCE_NAME}")
    if facts.get("publicly_accessible") is True:
        errors.append("restored instance must not be public")
    if facts.get("points_traffic") is True:
        errors.append("restored instance must not receive traffic")
    if not facts.get("schema_ok"):
        errors.append("schema checks are required")
    if not facts.get("counts_ok"):
        errors.append("count and tenant invariant checks are required")
    if not facts.get("rpo_observed") or not facts.get("rto_observed"):
        errors.append("observed RPO and RTO must be recorded")
    return errors


def render_checklist() -> str:
    lines = ["# Isolated restore test", ""]
    for step in RESTORE_STEPS:
        lines.append(f"1. {step}")
    lines.append("")
    lines.append(f"Isolated identifier: `{RESTORE_INSTANCE_NAME}`.")
    lines.append("")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-checklist", action="store_true")
    parser.add_argument("--environment", default="dev")
    parser.add_argument("--application-url", default="")
    parser.add_argument("--restore-endpoint", default="")
    parser.add_argument("--facts-json")
    args = parser.parse_args(argv)

    if args.print_checklist:
        print(render_checklist(), end="")
        if not args.restore_endpoint and not args.facts_json:
            return 0
    name = isolated_restore_name(args.environment)
    print(name)
    if args.restore_endpoint:
        refuse_production_traffic(args.application_url, args.restore_endpoint)
    if args.facts_json:
        facts = json.loads(args.facts_json)
        errors = review_restore_facts(facts)
        if errors:
            raise SystemExit("\n".join(errors))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
