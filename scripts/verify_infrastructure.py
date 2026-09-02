#!/usr/bin/env python3
"""Review non-sensitive Terraform outputs and post-apply AWS facts."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REQUIRED_OUTPUTS = (
    "environment",
    "aws_account_id",
    "application_url",
    "cloudfront_distribution_id",
    "api_health_url",
    "ecr_repository_url",
    "ecs_cluster_name",
    "ecs_service_name",
    "data_bucket_name",
    "web_bucket_name",
    "rds_identifier",
    "cognito_user_pool_id",
    "private_subnet_ids",
    "ecs_security_group_id",
)
SENSITIVE_KEY_FRAGMENTS = (
    "password",
    "database_url",
    "private_key",
    "access_key",
    "pepper",
    "secret_value",
)


def flatten_outputs(raw: Mapping[str, Any]) -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key, value in raw.items():
        if isinstance(value, dict) and "value" in value:
            flattened[str(key)] = value.get("value")
            if value.get("sensitive"):
                flattened[str(key)] = "(redacted)"
        else:
            flattened[str(key)] = value
    return flattened


def _looks_sensitive(key: str) -> bool:
    lowered = key.lower()
    return any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS)


def reject_sensitive_outputs(outputs: Mapping[str, Any]) -> list[str]:
    return [key for key in outputs if _looks_sensitive(str(key))]


def check_outputs(
    outputs: Mapping[str, Any],
    *,
    expected_environment: str,
    expected_account: str = "",
) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED_OUTPUTS:
        value = outputs.get(key)
        if value in (None, "", [], {}):
            errors.append(f"missing output {key}")
    environment = str(outputs.get("environment") or "")
    if expected_environment and environment != expected_environment:
        errors.append(
            f"output environment {environment} does not match {expected_environment}"
        )
    account = str(outputs.get("aws_account_id") or "")
    if expected_account and account != expected_account:
        errors.append("output account does not match the expected account")
    for key in reject_sensitive_outputs(outputs):
        errors.append(f"sensitive output {key} must not be printed")
    return errors


def check_facts(facts: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if facts.get("rds_publicly_accessible") is True:
        errors.append("RDS must not be publicly accessible")
    if facts.get("data_bucket_public") is True or facts.get("web_bucket_public") is True:
        errors.append("application buckets must stay private")
    if facts.get("vpc_id") in (None, ""):
        errors.append("VPC must be present")
    subnets = facts.get("private_subnet_ids") or []
    if not isinstance(subnets, list) or len(subnets) < 2:
        errors.append("private subnets must be present")
    if facts.get("ecs_security_group_id") in (None, ""):
        errors.append("ECS security group must be present")
    for key in ("ecr_repository_url", "ecs_cluster_name", "alb_arn", "log_group_name"):
        if facts.get(key) in (None, ""):
            errors.append(f"{key} must be present")
    cognito = facts.get("cognito_user_pool_id") in (None, "")
    cloudfront = facts.get("cloudfront_distribution_id") in (None, "")
    if cognito or cloudfront:
        errors.append("Cognito and CloudFront must be present")
    return errors


def public_outputs(outputs: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in outputs.items() if not _looks_sensitive(str(key))}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-json", type=Path)
    parser.add_argument("--facts-json", type=Path)
    parser.add_argument("--environment", default="dev")
    parser.add_argument("--account", default="")
    args = parser.parse_args(argv)

    raw: dict[str, Any]
    if args.from_json is None or str(args.from_json) == "-":
        raw = json.load(sys.stdin)
    else:
        raw = json.loads(args.from_json.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SystemExit("Terraform outputs must be a JSON object")
    outputs = flatten_outputs(raw)
    errors = check_outputs(
        outputs,
        expected_environment=args.environment,
        expected_account=args.account,
    )
    if args.facts_json:
        facts = json.loads(args.facts_json.read_text(encoding="utf-8"))
        if isinstance(facts, dict):
            errors.extend(check_facts(facts))
    print(json.dumps(public_outputs(outputs), indent=2, default=str))
    if errors:
        sys.stderr.write("Infrastructure verification failed:\n" + "\n".join(errors) + "\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
