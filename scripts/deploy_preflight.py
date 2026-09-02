#!/usr/bin/env python3
"""Secret-free deploy preflight. Does not apply Terraform or print credentials."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
DIGEST_RE = re.compile(r"@sha256:[A-Fa-f0-9]{64}$|^sha256:[A-Fa-f0-9]{64}$")
ACCOUNT_RE = re.compile(r"^[0-9]{12}$")
REGION_RE = re.compile(r"^[a-z]{2}-[a-z0-9-]+-\d+$")
PLACEHOLDER_ACCOUNT = "000000000000"

PREFLIGHT_ITEMS: tuple[dict[str, str], ...] = (
    {
        "id": "ci_main_green",
        "summary": "CI on main is green",
    },
    {
        "id": "api_image_digest",
        "summary": "API image is built, scanned, and published by digest",
    },
    {
        "id": "frontend_artifact",
        "summary": "Frontend artifact is built",
    },
    {
        "id": "openapi_sync",
        "summary": "OpenAPI and generated client are synchronized",
    },
    {
        "id": "migration_reviewed",
        "summary": "Migration is reviewed and expand-compatible",
    },
    {
        "id": "aws_identity",
        "summary": "AWS identity shows the expected account, role, and region",
    },
    {
        "id": "budget_reviewed",
        "summary": "Budget and dated official cost estimate are reviewed",
    },
    {
        "id": "bedrock_or_stub",
        "summary": "Bedrock model access is confirmed, or the copilot stays stub",
    },
    {
        "id": "backup_reviewed",
        "summary": "Backup or snapshot matches the change risk",
    },
)


def _load_script(name: str) -> ModuleType:
    path = REPO_ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def render_checklist() -> str:
    lines = [
        "# Deploy preflight",
        "",
        "Complete these checks before bootstrap, plan, or apply. Never paste secrets.",
        "",
    ]
    for item in PREFLIGHT_ITEMS:
        lines.append(f"- [ ] {item['summary']}")
    lines.append("")
    return "\n".join(lines)


def reject_latest_digest(image_digest: str) -> None:
    value = image_digest.strip()
    if not value:
        raise ValueError("image digest is required")
    if value.endswith(":latest") or value.endswith(":LATEST") or value == "latest":
        raise ValueError("image digest must not use the latest tag")
    if DIGEST_RE.search(value) is None:
        raise ValueError("image digest must be a digest identity")


def application_uses_https(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme == "https":
        return True
    host = (parsed.hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "::1"}


def evaluate_preflight(
    *,
    environment: str,
    image_digest: str = "",
    frontend_artifact: str = "",
    openapi_snapshot: str = "",
    ci_status: str = "",
    aws_account: str = "",
    aws_role: str = "",
    aws_region: str = "",
    ai_provider: str = "stub",
    bedrock_model_id: str = "",
    migration_reviewed: bool = False,
    budget_reviewed: bool = False,
    backup_reviewed: bool = False,
    first_apply: bool = False,
    require_gates: bool = False,
    repo_root: Path = REPO_ROOT,
    from_env: bool = False,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    items: dict[str, str] = {}
    errors: list[str] = []

    if ci_status.strip().lower() in {"green", "success", "passed"}:
        items["ci_main_green"] = "passed"
    else:
        errors.append("CI on main must be recorded as green")
        items["ci_main_green"] = "missing"

    if first_apply and not image_digest.strip():
        items["api_image_digest"] = "first-apply"
    else:
        try:
            reject_latest_digest(image_digest)
            items["api_image_digest"] = image_digest
        except ValueError as error:
            errors.append(str(error))
            items["api_image_digest"] = "invalid"

    artifact = Path(frontend_artifact) if frontend_artifact else (
        repo_root / "apps" / "web" / "out" / "index.html"
    )
    snapshot = Path(openapi_snapshot) if openapi_snapshot else (
        repo_root / "packages" / "api-client" / "openapi.json"
    )
    if artifact.is_file() or frontend_artifact in {"built", "artifact"}:
        items["frontend_artifact"] = "present"
    else:
        errors.append("frontend artifact is missing")
        items["frontend_artifact"] = "missing"
    if snapshot.is_file():
        items["openapi_sync"] = "present"
    else:
        errors.append("OpenAPI snapshot is missing")
        items["openapi_sync"] = "missing"

    if migration_reviewed:
        items["migration_reviewed"] = "reviewed"
    else:
        errors.append("migration must be reviewed and expand-compatible")
        items["migration_reviewed"] = "missing"

    account = aws_account.strip()
    role = aws_role.strip()
    region = aws_region.strip()
    valid_account = ACCOUNT_RE.fullmatch(account) and account != PLACEHOLDER_ACCOUNT
    if valid_account and role and REGION_RE.fullmatch(region):
        items["aws_identity"] = f"{account} {role} {region}"
    else:
        errors.append("AWS identity must record the expected account, role, and region")
        items["aws_identity"] = "missing"

    if budget_reviewed:
        items["budget_reviewed"] = "reviewed"
    else:
        errors.append("budget and dated official estimate must be reviewed")
        items["budget_reviewed"] = "missing"

    provider = ai_provider.strip().lower() or "stub"
    if provider == "stub":
        items["bedrock_or_stub"] = "stub"
    elif provider == "bedrock" and bedrock_model_id.strip():
        items["bedrock_or_stub"] = bedrock_model_id.strip()
    else:
        errors.append("Bedrock model access must be confirmed, or the copilot must stay stub")
        items["bedrock_or_stub"] = "missing"

    if backup_reviewed:
        items["backup_reviewed"] = "reviewed"
    else:
        errors.append("backup or snapshot must match the change risk")
        items["backup_reviewed"] = "missing"

    missing_gates: list[str] = []
    if require_gates:
        gates = _load_script("record_gate")
        missing_gates = list(
            gates.check_scope(
                "apply" if environment != "prod" else "prod",
                environment,
                repo_root=repo_root,
                from_env=from_env,
                environ=environ,
                ai_provider=provider,
            )
        )
        if missing_gates:
            errors.append("required gates are missing: " + ", ".join(missing_gates))

    return {
        "ok": not errors,
        "environment": environment,
        "items": items,
        "errors": errors,
        "missing_gates": missing_gates,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-checklist", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--environment", default="dev")
    parser.add_argument("--image-digest", default="")
    parser.add_argument("--frontend-artifact", default="")
    parser.add_argument("--openapi-snapshot", default="")
    parser.add_argument("--ci-status", default="")
    parser.add_argument("--account", default="")
    parser.add_argument("--role", default="")
    parser.add_argument("--region", default="")
    parser.add_argument("--ai-provider", default="stub")
    parser.add_argument("--bedrock-model-id", default="")
    parser.add_argument("--migration-reviewed", action="store_true")
    parser.add_argument("--budget-reviewed", action="store_true")
    parser.add_argument("--backup-reviewed", action="store_true")
    parser.add_argument("--first-apply", action="store_true")
    parser.add_argument("--require-gates", action="store_true")
    parser.add_argument("--from-env", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    if args.print_checklist:
        print(render_checklist(), end="")
        if not args.check:
            return 0

    if not args.check:
        parser.error("use --print-checklist and/or --check")

    result = evaluate_preflight(
        environment=args.environment,
        image_digest=args.image_digest,
        frontend_artifact=args.frontend_artifact,
        openapi_snapshot=args.openapi_snapshot,
        ci_status=args.ci_status,
        aws_account=args.account,
        aws_role=args.role,
        aws_region=args.region,
        ai_provider=args.ai_provider,
        bedrock_model_id=args.bedrock_model_id,
        migration_reviewed=args.migration_reviewed,
        budget_reviewed=args.budget_reviewed,
        backup_reviewed=args.backup_reviewed,
        first_apply=args.first_apply,
        require_gates=args.require_gates,
        from_env=args.from_env,
    )
    payload = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
        print(args.output)
    else:
        print(payload, end="")
    if not result["ok"]:
        for error in result["errors"]:
            print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
