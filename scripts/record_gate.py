#!/usr/bin/env python3
"""Record and check human-only manual gates. This script never stores secrets."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

GATE_IDS = tuple(f"M-{index:02d}" for index in range(0, 11))
REQUIRED_FIELDS = (
    "gate",
    "name",
    "status",
    "recorded_at",
    "recorded_by",
    "environment",
    "deliverables",
)
STATUSES = frozenset({"complete", "waived"})
ENVIRONMENTS = frozenset({"local", "dev", "prod"})
SCOPES = frozenset({"local", "plan", "apply", "aws", "prod"})
CREDENTIAL_METHODS = frozenset({"sso", "oidc", "assumed_role", "identity_center"})
AGENT_RECORDERS = frozenset({"agent", "auto", "default", "cursor"})
PROTECTED_GATES = frozenset({"M-01", "M-03", "M-07", "M-08", "M-09", "M-10"})
PLACEHOLDER_ACCOUNT = "000000000000"
ACCOUNT_RE = re.compile(r"^[0-9]{12}$")
REGION_RE = re.compile(r"^[a-z]{2}-[a-z0-9-]+-\d+$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DIGEST_RE = re.compile(r"@sha256:[A-Fa-f0-9]{64}$")
YES_VALUES = frozenset({"yes", "true", "1", "confirmed"})

FORBIDDEN_DELIVERABLE_KEYS = frozenset(
    {
        "password",
        "root_password",
        "aws_secret_access_key",
        "secret_access_key",
        "secret_key",
        "database_password",
        "database_url",
        "cognito_token",
        "id_token",
        "access_token",
        "refresh_token",
        "private_key",
        "tfstate",
        "plan_json",
        "plan_file",
    }
)
SECRET_VALUE_RE = re.compile(
    r"(AKIA[0-9A-Z]{16}|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY|"
    r"postgresql(?:\+psycopg)?://[^:\s]+:[^@\s]+@)",
    re.IGNORECASE,
)
FORBIDDEN_IN_PLANS = (
    "AWS root password",
    "secret access key pasted in chat or Git",
    "production database password",
    "Cognito token",
    "real financial file contents",
    "complete Terraform plan or state with sensitive values",
)

FUNCTIONAL_DEFAULTS: dict[str, str] = {
    "fiscal_year_convention": "calendar months; start month is configurable per organization",
    "demo_currency": "one functional currency; Alpha MXN (January), Beta USD (April)",
    "favorability_rules": "expense over budget is unfavorable; revenue over budget is favorable",
    "actuals_mode": "actuals accumulate by import batch; explicit range replace is deferred",
    "product_language": "Spanish product copy; repository documentation stays English",
}

SCOPE_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "local": (),
    "plan": ("M-01", "M-02"),
    "apply": ("M-01", "M-02", "M-03", "M-09"),
    "aws": ("M-01", "M-02", "M-03", "M-05", "M-09"),
    "prod": ("M-01", "M-02", "M-03", "M-05", "M-06", "M-07", "M-08", "M-09", "M-10"),
}

GATE_SPECS: dict[str, dict[str, Any]] = {
    "M-00": {
        "name": "Functional defaults",
        "owner": "Domain owner",
        "moment": "Before or during plan 01",
        "local_simulation": "Yes, defaults",
        "blocks": "No if defaults are accepted",
        "required_deliverables": (),
        "optional_deliverables": tuple(FUNCTIONAL_DEFAULTS),
        "defaults_accepted": True,
        "human_actions": (
            "Confirm fiscal-year convention, demo currency, favorability, "
            "actuals mode, and product language, or accept the spec defaults.",
        ),
        "waivable": False,
    },
    "M-01": {
        "name": "Secure AWS account",
        "owner": "Security owner",
        "moment": "Before a real terraform plan",
        "local_simulation": "No",
        "blocks": "AWS",
        "required_deliverables": ("aws_account_id", "credential_method", "profile_or_role"),
        "optional_deliverables": ("owner", "cost_center"),
        "human_actions": (
            "Create or select the account and payment method.",
            "Enable root MFA. Do not use root for deploys.",
            "Configure IAM Identity Center or an equivalent administrative identity.",
            "Record the account ID and owner/cost-center tags.",
        ),
        "waivable": False,
    },
    "M-02": {
        "name": "Region",
        "owner": "Operator",
        "moment": "Before remote bootstrap",
        "local_simulation": "Fake config",
        "blocks": "AWS",
        "required_deliverables": ("primary_region",),
        "optional_deliverables": ("bedrock_available", "acm_cloudfront_notes"),
        "human_actions": (
            "Choose the primary region after Bedrock, service, residency, "
            "latency, price, and ACM/CloudFront review.",
        ),
        "waivable": False,
    },
    "M-03": {
        "name": "Budget",
        "owner": "Operator",
        "moment": "Before apply",
        "local_simulation": "Terraform code",
        "blocks": "AWS",
        "required_deliverables": (
            "budget_limit",
            "alert_email",
            "email_subscription_confirmed",
            "cost_estimate_recorded",
        ),
        "optional_deliverables": (),
        "human_actions": (
            "Choose budget limits and thresholds.",
            "Name the alert email or SNS target.",
            "Confirm the AWS subscription email when it arrives.",
            "Review a dated official cost estimate.",
        ),
        "waivable": False,
    },
    "M-04": {
        "name": "Bedrock model access",
        "owner": "AI owner",
        "moment": "Live eval and AWS AI",
        "local_simulation": "Stub/contract mock",
        "blocks": "AWS AI",
        "required_deliverables": ("model_id",),
        "optional_deliverables": ("live_eval_approved",),
        "human_actions": (
            "Select a model that supports the required tool use.",
            "Accept terms or request access if the account or region requires it.",
            "Record the exact model ID as an environment variable. "
            "Do not hardcode a commercial name in domain code.",
            "Run live evaluation and approve results and cost.",
        ),
        "waivable": True,
        "waive_reason": "ai_provider=stub completes local and AWS deploys without live access",
    },
    "M-05": {
        "name": "GitHub/OIDC",
        "owner": "Engineering",
        "moment": "Real pipeline enablement",
        "local_simulation": "Workflow lint",
        "blocks": "Real pipeline",
        "required_deliverables": ("github_owner_repo", "environments_configured", "oidc_allowed"),
        "optional_deliverables": ("branch_protection",),
        "human_actions": (
            "Create or select the remote repository.",
            "Enable branch protection.",
            "Create GitHub Environments dev and prod with reviewers.",
            "Allow OIDC and Actions according to repository policy.",
        ),
        "waivable": False,
    },
    "M-06": {
        "name": "Domain/DNS",
        "owner": "Operator",
        "moment": "Before a final production URL",
        "local_simulation": "Managed domain",
        "blocks": "Production URL",
        "required_deliverables": ("domain_name", "dns_provider", "callback_urls"),
        "optional_deliverables": ("logout_urls",),
        "human_actions": (
            "Buy or select the domain.",
            "Choose Route 53 or an external DNS provider.",
            "Authorize ACM and Cognito validation records.",
            "Define callback and logout URLs.",
        ),
        "waivable": True,
        "waive_reason": "development may use CloudFront and Cognito managed domains",
    },
    "M-07": {
        "name": "Users",
        "owner": "Security owner",
        "moment": "Before third-party users",
        "local_simulation": "Test issuer/JWKS",
        "blocks": "Third-party users",
        "required_deliverables": (
            "registration_mode",
            "mfa_policy",
            "account_recovery",
            "first_admin_process",
        ),
        "optional_deliverables": ("terms_privacy",),
        "human_actions": (
            "Choose open registration versus invitation.",
            "Decide MFA required or optional.",
            "Define account recovery and the first admin process.",
            "Record terms and privacy if external users will sign in.",
        ),
        "waivable": True,
        "waive_reason": "self-registration stays off until third-party users are enabled",
    },
    "M-08": {
        "name": "Data and chat policy",
        "owner": "Product/Security",
        "moment": "Before real data",
        "local_simulation": "Local synthetic policy",
        "blocks": "Real data",
        "required_deliverables": (
            "data_classification",
            "retention_policy",
            "conversation_persistence",
            "operator_access",
            "deletion_export_process",
        ),
        "optional_deliverables": (),
        "human_actions": (
            "Classify data and residency.",
            "Set retention for uploads, exports, audit, and chat.",
            "Decide whether full conversation text is stored.",
            "Define operator access and deletion or export.",
            "Accept ADR-012 before real customer data.",
        ),
        "waivable": True,
        "waive_reason": "synthetic local and redacted cloud storage until ADR-012 is accepted",
    },
    "M-09": {
        "name": "Apply review",
        "owner": "Operator",
        "moment": "Immediately before apply",
        "local_simulation": "No",
        "blocks": "AWS apply",
        "required_deliverables": (
            "aws_account",
            "aws_role",
            "aws_region",
            "plan_reviewed",
            "destroys_reviewed",
            "cost_estimate_reviewed",
            "image_digest",
            "migration_reviewed",
            "dns_callbacks_reviewed",
        ),
        "optional_deliverables": (),
        "human_actions": (
            "Confirm AWS identity (account, role, region).",
            "Review the Terraform plan, especially destroys and replacements.",
            "Review the dated estimate and expensive resources.",
            "Confirm the image digest.",
            "Review the migration.",
            "Review DNS and callback URLs.",
            "Authorize apply only after that review.",
        ),
        "waivable": False,
    },
    "M-10": {
        "name": "Production",
        "owner": "Owner",
        "moment": "Future production cutover",
        "local_simulation": "No",
        "blocks": "Production",
        "required_deliverables": (
            "prod_account_or_environment",
            "threat_privacy_review",
            "restore_test",
            "live_ai_eval",
            "incident_ownership",
            "plan_and_window_approved",
        ),
        "optional_deliverables": (),
        "human_actions": (
            "Provision a production account or environment.",
            "Complete threat and privacy review, restore test, and live AI evaluation.",
            "Assign incident ownership.",
            "Approve the plan and change window.",
        ),
        "waivable": False,
    },
}


def default_output(environment: str, gate: str, *, repo_root: Path = REPO_ROOT) -> Path:
    return repo_root / "var" / "gates" / f"{environment}-{gate}.json"


def parse_deliverable(raw: str) -> tuple[str, str]:
    key, separator, value = raw.partition("=")
    if not separator or not key.strip():
        raise ValueError("deliverable must be key=value")
    return key.strip(), value.strip()


def truthy(value: object) -> bool:
    return str(value or "").strip().lower() in YES_VALUES


def reject_forbidden_deliverables(deliverables: Mapping[str, Any]) -> None:
    for key, value in deliverables.items():
        lowered = key.strip().lower()
        if lowered in FORBIDDEN_DELIVERABLE_KEYS or any(
            token in lowered for token in ("password", "secret", "token", "private_key")
        ):
            raise ValueError(f"deliverable {key} is forbidden; never record secrets")
        text = str(value)
        if SECRET_VALUE_RE.search(text):
            raise ValueError("deliverable value looks like a secret and must not be recorded")


def _require(deliverables: Mapping[str, Any], key: str) -> str:
    value = str(deliverables.get(key, "")).strip()
    if not value:
        raise ValueError(f"{key} is required")
    return value


def validate_deliverables(gate: str, deliverables: Mapping[str, Any], *, status: str) -> None:
    spec = GATE_SPECS[gate]
    reject_forbidden_deliverables(deliverables)
    if status == "waived":
        if not spec.get("waivable"):
            raise ValueError(f"{gate} cannot be waived")
        return
    for key in spec["required_deliverables"]:
        _require(deliverables, key)
    if gate == "M-01":
        account = _require(deliverables, "aws_account_id")
        if account == PLACEHOLDER_ACCOUNT or not ACCOUNT_RE.fullmatch(account):
            raise ValueError("aws_account_id must be the real 12-digit account, not a placeholder")
        method = _require(deliverables, "credential_method")
        if method not in CREDENTIAL_METHODS:
            raise ValueError(
                "credential_method must be sso, oidc, assumed_role, or identity_center"
            )
        role = _require(deliverables, "profile_or_role")
        if role.lower() in {"root", "aws-root"}:
            raise ValueError("do not use the AWS root user for deploys")
        return
    if gate == "M-02":
        region = _require(deliverables, "primary_region")
        if not REGION_RE.fullmatch(region):
            raise ValueError("primary_region must be an AWS region id such as us-east-1")
        return
    if gate == "M-03":
        _require(deliverables, "budget_limit")
        email = _require(deliverables, "alert_email")
        if not EMAIL_RE.fullmatch(email):
            raise ValueError("alert_email must be an email address, not an SNS confirmation token")
        if not truthy(deliverables.get("email_subscription_confirmed")):
            raise ValueError("email_subscription_confirmed must be an explicit human yes")
        if not truthy(deliverables.get("cost_estimate_recorded")):
            raise ValueError("cost_estimate_recorded must be an explicit human yes")
        return
    if gate == "M-04":
        model_id = _require(deliverables, "model_id")
        if model_id.lower() in {"claude", "sonnet", "haiku", "titan"}:
            raise ValueError("record the exact model ID, not a commercial name")
        return
    if gate == "M-05":
        owner_repo = _require(deliverables, "github_owner_repo")
        if "/" not in owner_repo:
            raise ValueError("github_owner_repo must be owner/name")
        if not truthy(deliverables.get("environments_configured")):
            raise ValueError("environments_configured must be an explicit human yes")
        if not truthy(deliverables.get("oidc_allowed")):
            raise ValueError("oidc_allowed must be an explicit human yes")
        return
    if gate == "M-09":
        account = _require(deliverables, "aws_account")
        if account == PLACEHOLDER_ACCOUNT or not ACCOUNT_RE.fullmatch(account):
            raise ValueError("aws_account must be the caller account ID")
        _require(deliverables, "aws_role")
        region = _require(deliverables, "aws_region")
        if not REGION_RE.fullmatch(region):
            raise ValueError("aws_region must be an AWS region id")
        for key in (
            "plan_reviewed",
            "destroys_reviewed",
            "cost_estimate_reviewed",
            "migration_reviewed",
            "dns_callbacks_reviewed",
        ):
            if not truthy(deliverables.get(key)):
                raise ValueError(f"{key} must be an explicit human yes")
        digest = _require(deliverables, "image_digest")
        if digest != "first-apply" and not DIGEST_RE.search(digest):
            raise ValueError("image_digest must be a repository@sha256:… URI or first-apply")
        return


def validate_record(record: Mapping[str, Any]) -> None:
    missing = [field for field in REQUIRED_FIELDS if field not in record]
    if missing:
        raise ValueError(f"gate record is missing fields: {', '.join(missing)}")
    gate = str(record.get("gate") or "")
    if gate not in GATE_SPECS:
        raise ValueError(f"unknown gate: {gate}")
    if record.get("name") != GATE_SPECS[gate]["name"]:
        raise ValueError("gate name does not match the catalog")
    status = str(record.get("status") or "")
    if status not in STATUSES:
        raise ValueError("status must be complete or waived")
    environment = str(record.get("environment") or "")
    if environment not in ENVIRONMENTS:
        raise ValueError("environment must be local, dev, or prod")
    recorded_at = str(record.get("recorded_at") or "")
    if not re.match(r"^\d{4}-\d{2}-\d{2}", recorded_at):
        raise ValueError("recorded_at must be an ISO date")
    recorded_by = str(record.get("recorded_by") or "").strip()
    if not recorded_by:
        raise ValueError("recorded_by is required")
    if gate in PROTECTED_GATES and recorded_by.lower() in AGENT_RECORDERS:
        raise ValueError(f"{gate} requires a human recorded_by; an agent cannot accept it")
    if gate == "M-09" and record.get("confirmed") is not True:
        raise ValueError("M-09 requires confirmed=true after the apply checklist")
    if status == "waived" and not str(record.get("notes") or "").strip():
        raise ValueError("a waived gate needs a notes reason")
    if gate == "M-06" and status == "waived" and environment == "prod":
        raise ValueError("M-06 cannot be waived for production")
    raw_deliverables = record.get("deliverables")
    if not isinstance(raw_deliverables, Mapping):
        raise ValueError("deliverables must be an object")
    deliverables = {str(key): value for key, value in raw_deliverables.items()}
    validate_deliverables(gate, deliverables, status=status)


def build_record(
    *,
    gate: str,
    recorded_by: str,
    environment: str,
    deliverables: Mapping[str, Any] | None = None,
    status: str = "complete",
    recorded_at: str = "",
    notes: str = "",
    confirmed: bool = False,
) -> dict[str, Any]:
    if gate not in GATE_SPECS:
        raise ValueError(f"unknown gate: {gate}")
    payload = dict(deliverables or {})
    if gate == "M-00" and status == "complete" and not payload:
        payload = dict(FUNCTIONAL_DEFAULTS)
    record: dict[str, Any] = {
        "gate": gate,
        "name": GATE_SPECS[gate]["name"],
        "status": status,
        "recorded_at": recorded_at.strip() or datetime.now(UTC).date().isoformat(),
        "recorded_by": recorded_by.strip(),
        "environment": environment,
        "deliverables": payload,
        "notes": notes.strip(),
    }
    if gate == "M-09":
        record["confirmed"] = confirmed is True
    validate_record(record)
    return record


def evidence_from_env(environ: Mapping[str, str]) -> dict[str, dict[str, str]]:
    account = (environ.get("AWS_ACCOUNT_ID") or "").strip()
    region = (environ.get("AWS_REGION") or "").strip()
    role = (
        environ.get("PLAN_ROLE_ARN")
        or environ.get("DEPLOY_DEV_ROLE_ARN")
        or environ.get("DEPLOY_PROD_ROLE_ARN")
        or environ.get("AWS_ROLE_ARN")
        or environ.get("AWS_PROFILE")
        or ""
    ).strip()
    evidence: dict[str, dict[str, str]] = {}
    if ACCOUNT_RE.fullmatch(account) and account != PLACEHOLDER_ACCOUNT and role:
        method = "oidc" if role.startswith("arn:") else "sso"
        evidence["M-01"] = {
            "aws_account_id": account,
            "credential_method": method,
            "profile_or_role": role,
        }
    if REGION_RE.fullmatch(region):
        evidence["M-02"] = {"primary_region": region}
    return evidence


def load_record(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("gate file must be a JSON object")
    record = {str(key): value for key, value in payload.items()}
    validate_record(record)
    return record


def load_records(
    environment: str,
    *,
    repo_root: Path = REPO_ROOT,
    extra: Mapping[str, Mapping[str, str]] | None = None,
) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    folder = repo_root / "var" / "gates"
    if folder.is_dir():
        for path in sorted(folder.glob(f"{environment}-M-*.json")):
            record = load_record(path)
            records[str(record["gate"])] = record
    for gate, deliverables in (extra or {}).items():
        if gate in records:
            continue
        if gate == "M-01":
            records[gate] = {
                "gate": gate,
                "name": GATE_SPECS[gate]["name"],
                "status": "complete",
                "recorded_at": datetime.now(UTC).date().isoformat(),
                "recorded_by": "github-vars",
                "environment": environment,
                "deliverables": dict(deliverables),
                "notes": "synthesized from GitHub or process environment variables",
            }
            validate_record(records[gate])
        elif gate == "M-02":
            records[gate] = {
                "gate": gate,
                "name": GATE_SPECS[gate]["name"],
                "status": "complete",
                "recorded_at": datetime.now(UTC).date().isoformat(),
                "recorded_by": "github-vars",
                "environment": environment,
                "deliverables": dict(deliverables),
                "notes": "synthesized from GitHub or process environment variables",
            }
            validate_record(records[gate])
    return records


def required_gates(scope: str, *, ai_provider: str = "stub") -> list[str]:
    if scope not in SCOPE_REQUIREMENTS:
        raise ValueError(f"scope must be one of {', '.join(sorted(SCOPES))}")
    required = list(SCOPE_REQUIREMENTS[scope])
    if ai_provider == "bedrock" and "M-04" not in required:
        required.append("M-04")
    return required


def missing_gates(
    scope: str,
    records: Mapping[str, Mapping[str, Any]],
    *,
    ai_provider: str = "stub",
) -> list[str]:
    missing: list[str] = []
    for gate in required_gates(scope, ai_provider=ai_provider):
        record = records.get(gate)
        if record is None:
            missing.append(gate)
            continue
        try:
            validate_record(record)
        except ValueError:
            missing.append(gate)
    return missing


def check_scope(
    scope: str,
    environment: str,
    *,
    repo_root: Path = REPO_ROOT,
    environ: Mapping[str, str] | None = None,
    from_env: bool = False,
    ai_provider: str = "stub",
) -> list[str]:
    extra = evidence_from_env(environ or {}) if from_env else None
    records = load_records(environment, repo_root=repo_root, extra=extra)
    return missing_gates(scope, records, ai_provider=ai_provider)


def render_checklist(gate: str) -> str:
    spec = GATE_SPECS[gate]
    lines = [
        f"# {gate} — {spec['name']}",
        "",
        f"- **Owner:** {spec['owner']}",
        f"- **When:** {spec['moment']}",
        f"- **Blocks:** {spec['blocks']}",
        f"- **Local simulation:** {spec['local_simulation']}",
        "",
        "A human must complete this gate. Code must not assume the decision.",
        "",
        "## Actions",
        "",
    ]
    for action in spec["human_actions"]:
        lines.append(f"- [ ] {action}")
    required = spec["required_deliverables"]
    if required:
        lines.extend(["", "## Deliverables (never secrets)", ""])
        for key in required:
            lines.append(f"- `{key}`")
    if spec.get("waivable"):
        lines.extend(["", f"This gate may be waived: {spec['waive_reason']}."])
    lines.append("")
    return "\n".join(lines)


def render_index() -> str:
    lines = [
        "# Manual gates",
        "",
        "These are the only decisions the code must not assume.",
        "Local work uses defaults and stubs.",
        "",
        "| Gate | Name | Owner | When | Blocks |",
        "|---|---|---|---|---|",
    ]
    for gate_id, spec in GATE_SPECS.items():
        lines.append(
            "| "
            f"{gate_id} | {spec['name']} | {spec['owner']} | "
            f"{spec['moment']} | {spec['blocks']} |"
        )
    lines.extend(
        [
            "",
            "## Never request in a plan",
            "",
        ]
    )
    for item in FORBIDDEN_IN_PLANS:
        lines.append(f"- {item}")
    lines.extend(["", "## Functional defaults (M-00)", ""])
    for key, value in FUNCTIONAL_DEFAULTS.items():
        lines.append(f"- **{key}:** {value}")
    lines.append("")
    return "\n".join(lines)


def render_markdown(record: Mapping[str, Any]) -> str:
    lines = [
        f"# {record['gate']} — {record['name']}",
        "",
        "This file records a human decision. It must not contain secrets.",
        "",
        f"- **status:** {record['status']}",
        f"- **recorded_at:** {record['recorded_at']}",
        f"- **recorded_by:** {record['recorded_by']}",
        f"- **environment:** {record['environment']}",
        "",
        "## Deliverables",
        "",
    ]
    raw = record.get("deliverables") or {}
    if isinstance(raw, Mapping):
        deliverables = {str(key): value for key, value in raw.items()}
    else:
        deliverables = {}
    if not deliverables:
        lines.append("- (none; defaults accepted)")
    else:
        for key, value in deliverables.items():
            lines.append(f"- `{key}`: {value}")
    if record.get("notes"):
        lines.extend(["", f"- **notes:** {record['notes']}"])
    if record.get("confirmed") is True:
        lines.extend(["", "Apply review was confirmed by a human."])
    lines.append("")
    return "\n".join(lines)


def build_apply_review(
    *,
    environment: str,
    recorded_by: str,
    aws_account: str,
    aws_role: str,
    aws_region: str,
    image_digest: str,
    confirm: str,
    recorded_at: str = "",
    notes: str = "",
    first_apply: bool = False,
) -> dict[str, Any]:
    if confirm != "1":
        raise ValueError("Apply review requires CONFIRM=1 after the human checklist")
    digest = "first-apply" if first_apply and not image_digest.strip() else image_digest.strip()
    return build_record(
        gate="M-09",
        recorded_by=recorded_by,
        environment=environment,
        recorded_at=recorded_at,
        notes=notes,
        confirmed=True,
        deliverables={
            "aws_account": aws_account.strip(),
            "aws_role": aws_role.strip(),
            "aws_region": aws_region.strip(),
            "plan_reviewed": "yes",
            "destroys_reviewed": "yes",
            "cost_estimate_reviewed": "yes",
            "image_digest": digest,
            "migration_reviewed": "yes",
            "dns_callbacks_reviewed": "yes",
        },
    )


def write_record(record: Mapping[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(render_markdown(record), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--print-checklist", metavar="GATE")
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--review-apply", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--gate")
    parser.add_argument("--environment", default="dev")
    parser.add_argument("--recorded-by", default="")
    parser.add_argument("--status", choices=sorted(STATUSES), default="complete")
    parser.add_argument("--recorded-at", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--deliverable", action="append", default=[])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--scope", choices=sorted(SCOPES), default="apply")
    parser.add_argument("--from-env", action="store_true")
    parser.add_argument("--ai-provider", choices=("stub", "bedrock"), default="stub")
    parser.add_argument("--account", default="")
    parser.add_argument("--role", default="")
    parser.add_argument("--region", default="")
    parser.add_argument("--image-digest", default="")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--first-apply", action="store_true")
    parser.add_argument("--require-prior", action="store_true")
    args = parser.parse_args(argv)

    if args.list:
        print(render_index(), end="")
        return 0

    if args.print_checklist:
        gate = args.print_checklist
        if gate not in GATE_SPECS:
            raise SystemExit(f"unknown gate: {gate}")
        print(render_checklist(gate), end="")
        return 0

    if args.check:
        missing = check_scope(
            args.scope,
            args.environment,
            from_env=args.from_env,
            environ=os.environ,
            ai_provider=args.ai_provider,
        )
        if missing:
            print("Missing human gates: " + ", ".join(missing))
            print("Record them with scripts/record_gate.py. Do not paste secrets.")
            return 1
        print(f"{args.scope} gates are recorded for {args.environment}")
        return 0

    if args.review_apply:
        if args.require_prior:
            extra = evidence_from_env(os.environ) if args.from_env else None
            records = load_records(args.environment, extra=extra)
            missing = [gate for gate in ("M-01", "M-02", "M-03") if gate not in records]
            if missing:
                print("Missing human gates before apply: " + ", ".join(missing))
                return 1
        record = build_apply_review(
            environment=args.environment,
            recorded_by=args.recorded_by,
            aws_account=args.account,
            aws_role=args.role,
            aws_region=args.region,
            image_digest=args.image_digest,
            confirm=args.confirm,
            recorded_at=args.recorded_at,
            notes=args.notes,
            first_apply=args.first_apply,
        )
        output = args.output or default_output(record["environment"], record["gate"])
        write_record(record, output)
        print(output)
        return 0

    if args.record:
        if not args.gate:
            raise SystemExit("--gate is required with --record")
        deliverables = dict(parse_deliverable(item) for item in args.deliverable)
        record = build_record(
            gate=args.gate,
            recorded_by=args.recorded_by,
            environment=args.environment,
            deliverables=deliverables,
            status=args.status,
            recorded_at=args.recorded_at,
            notes=args.notes,
            confirmed=args.confirm == "1",
        )
        output = args.output or default_output(record["environment"], record["gate"])
        write_record(record, output)
        print(output)
        return 0

    raise SystemExit("Use --list, --print-checklist, --record, --check, or --review-apply")


if __name__ == "__main__":
    raise SystemExit(main())
