#!/usr/bin/env python3
"""Record a dated official AWS cost estimate. This script never invents a price."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
TF_ENV_ROOT = REPO_ROOT / "infrastructure" / "terraform" / "environments"

REQUIRED_FIELDS = (
    "recorded_at",
    "environment",
    "source",
    "currency",
    "monthly_estimate",
    "sizes",
    "estimate",
)
SIZE_KEYS = (
    "nat_gateway_count",
    "api_desired_count",
    "api_cpu",
    "api_memory",
    "db_instance_class",
    "db_allocated_storage",
    "db_multi_az",
    "log_retention_days",
    "enable_autoscaling",
    "backup_retention_days",
    "price_class",
    "ai_provider",
)
OFFICIAL_SOURCE_MARKERS = (
    "calculator.aws",
    "aws.amazon.com/pricing",
    "docs.aws.amazon.com",
    "AWS Price List",
    "pricing.aws",
)
TFVARS_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s*(?:#.*)?$")


def parse_tfvars(text: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = TFVARS_LINE.match(line)
        if not match:
            continue
        values[match.group(1)] = _parse_tfvars_value(match.group(2))
    return values


def _parse_tfvars_value(raw: str) -> Any:
    value = raw.strip()
    if value.startswith("[") or value.startswith("{"):
        return value
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    return value


def extract_sizes(values: Mapping[str, Any]) -> dict[str, Any]:
    missing = [key for key in SIZE_KEYS if key not in values]
    if missing:
        raise ValueError(f"tfvars is missing cost-visible sizes: {', '.join(missing)}")
    return {key: values[key] for key in SIZE_KEYS}


def load_environment_sizes(environment: str, *, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    path = repo_root / "infrastructure" / "terraform" / "environments" / environment / "terraform.tfvars"
    if not path.is_file():
        raise ValueError(f"Unknown environment tfvars: {environment}")
    return extract_sizes(parse_tfvars(path.read_text(encoding="utf-8")))


def official_source(source: str) -> bool:
    text = source.strip()
    return any(marker.lower() in text.lower() for marker in OFFICIAL_SOURCE_MARKERS)


def validate_record(record: Mapping[str, Any]) -> None:
    missing = [field for field in REQUIRED_FIELDS if field not in record]
    if missing:
        raise ValueError(f"cost estimate is missing fields: {', '.join(missing)}")
    if record.get("estimate") is not True:
        raise ValueError("cost estimate must set estimate=true; the amount is a human figure")
    if not official_source(str(record.get("source") or "")):
        raise ValueError(
            "source must be an official AWS calculator or price list "
            "(calculator.aws, aws.amazon.com/pricing, or AWS Price List)"
        )
    environment = str(record.get("environment") or "")
    if environment not in {"dev", "prod"}:
        raise ValueError("environment must be dev or prod")
    recorded_at = str(record.get("recorded_at") or "")
    if not re.match(r"^\d{4}-\d{2}-\d{2}", recorded_at):
        raise ValueError("recorded_at must be an ISO date")
    currency = str(record.get("currency") or "")
    if len(currency) != 3 or not currency.isalpha():
        raise ValueError("currency must be a 3-letter code")
    monthly = record.get("monthly_estimate")
    if monthly in (None, ""):
        raise ValueError("monthly_estimate must be provided by a human; this script does not invent a price")
    try:
        amount = float(str(monthly))
    except (TypeError, ValueError) as error:
        raise ValueError("monthly_estimate must be a number from the official calculator") from error
    if amount < 0:
        raise ValueError("monthly_estimate must be zero or positive")
    sizes = record.get("sizes")
    if not isinstance(sizes, Mapping):
        raise ValueError("sizes must be an object of Terraform counts and classes")
    missing_sizes = [key for key in SIZE_KEYS if key not in sizes]
    if missing_sizes:
        raise ValueError(f"sizes must include {', '.join(missing_sizes)}")


def build_record(
    *,
    environment: str,
    source: str,
    monthly_estimate: str,
    currency: str = "USD",
    recorded_at: str = "",
    notes: str = "",
    sizes: Mapping[str, Any] | None = None,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    stamp = recorded_at.strip() or datetime.now(UTC).date().isoformat()
    resolved_sizes = dict(sizes) if sizes is not None else load_environment_sizes(environment, repo_root=repo_root)
    record = {
        "recorded_at": stamp,
        "environment": environment,
        "source": source.strip(),
        "currency": currency.strip().upper(),
        "monthly_estimate": str(monthly_estimate).strip(),
        "sizes": resolved_sizes,
        "notes": notes.strip(),
        "estimate": True,
    }
    validate_record(record)
    return record


def check_record(record: Mapping[str, Any], current_sizes: Mapping[str, Any]) -> None:
    validate_record(record)
    drifted = [
        key
        for key in SIZE_KEYS
        if record["sizes"].get(key) != current_sizes.get(key)
    ]
    if drifted:
        raise ValueError(
            "Terraform sizes changed since the estimate; record a new dated estimate "
            f"for: {', '.join(drifted)}"
        )


def render_markdown(record: Mapping[str, Any]) -> str:
    lines = [
        "# Cost estimate",
        "",
        "This file is a dated human estimate from official AWS prices. It is not a quote.",
        "A budget is an alert, not a hard cap.",
        "",
        f"- **recorded_at:** {record['recorded_at']}",
        f"- **environment:** {record['environment']}",
        f"- **source:** {record['source']}",
        f"- **currency:** {record['currency']}",
        f"- **monthly_estimate:** {record['monthly_estimate']} (estimate)",
        "",
        "## Visible sizes",
        "",
    ]
    for key in SIZE_KEYS:
        lines.append(f"- `{key}`: {record['sizes'][key]}")
    if record.get("notes"):
        lines.extend(["", f"- **notes:** {record['notes']}"])
    lines.append("")
    return "\n".join(lines)


def default_output(environment: str, recorded_at: str, *, repo_root: Path = REPO_ROOT) -> Path:
    day = recorded_at[:10]
    return repo_root / "var" / "cost-estimates" / f"{environment}-{day}.json"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", choices=("dev", "prod"))
    parser.add_argument("--source", default="")
    parser.add_argument("--monthly-estimate", default="")
    parser.add_argument("--currency", default="USD")
    parser.add_argument("--recorded-at", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--print-sizes", action="store_true")
    parser.add_argument("--check", type=Path)
    args = parser.parse_args(argv)

    if args.print_sizes:
        environment = args.environment or "dev"
        sizes = load_environment_sizes(environment)
        print(json.dumps({"environment": environment, "sizes": sizes}, indent=2))
        return 0

    if args.check:
        record = json.loads(args.check.read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            raise ValueError("cost estimate file must be a JSON object")
        environment = str(record.get("environment") or args.environment or "")
        current = load_environment_sizes(environment)
        check_record(record, current)
        print(args.check)
        return 0

    if not args.environment:
        raise SystemExit("--environment is required unless --print-sizes or --check is used")
    if not args.source or not args.monthly_estimate:
        raise SystemExit(
            "Pass --source (official AWS calculator or price list) and --monthly-estimate. "
            "This script does not invent a price."
        )

    record = build_record(
        environment=args.environment,
        source=args.source,
        monthly_estimate=args.monthly_estimate,
        currency=args.currency,
        recorded_at=args.recorded_at,
        notes=args.notes,
    )
    output = args.output or default_output(record["environment"], record["recorded_at"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(render_markdown(record), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
