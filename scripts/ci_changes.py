#!/usr/bin/env python3
"""Classify changed paths for CI job selection."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ALWAYS_JOBS = ("security",)
PATH_JOBS = ("api", "web", "contract", "e2e", "terraform")

API_PREFIXES = (
    "apps/api/",
    ".python-version",
    "apps/api/pyproject.toml",
    "apps/api/uv.lock",
    "apps/api/alembic.ini",
)
WEB_PREFIXES = (
    "apps/web/",
    "package.json",
    "pnpm-lock.yaml",
    "pnpm-workspace.yaml",
    ".node-version",
)
CONTRACT_PREFIXES = (
    "apps/api/src/budgetlens/presentation/",
    "apps/api/tests/unit/test_openapi.py",
    "packages/api-client/",
    "scripts/export_openapi.py",
)
E2E_PREFIXES = (
    "apps/web/e2e/",
    "compose.yaml",
    "scripts/ci-e2e.sh",
    "scripts/acceptance-local-stack.sh",
)
TERRAFORM_PREFIXES = (
    "infrastructure/terraform/",
)
FORCE_ALL_PREFIXES = (
    ".github/workflows/",
    "scripts/ci.sh",
    "scripts/ci_changes.py",
    "scripts/scan.sh",
    "Makefile",
)


def _normalize(path: str) -> str:
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _matches(path: str, prefixes: Sequence[str]) -> bool:
    normalized = _normalize(path)
    return any(
        normalized == prefix.rstrip("/") or normalized.startswith(prefix)
        for prefix in prefixes
    )


def classify_paths(paths: Iterable[str]) -> dict[str, bool]:
    files = [_normalize(path) for path in paths if path.strip()]
    force_all = not files or any(_matches(path, FORCE_ALL_PREFIXES) for path in files)
    selected = {
        "api": force_all or any(_matches(path, API_PREFIXES) for path in files),
        "web": force_all or any(_matches(path, WEB_PREFIXES) for path in files),
        "contract": force_all or any(_matches(path, CONTRACT_PREFIXES) for path in files),
        "e2e": force_all
        or any(_matches(path, (*E2E_PREFIXES, *API_PREFIXES, *WEB_PREFIXES)) for path in files),
        "terraform": force_all or any(_matches(path, TERRAFORM_PREFIXES) for path in files),
        "security": True,
    }
    if selected["contract"]:
        selected["api"] = True
    return selected


def changed_files(base: str | None, event: str) -> list[str]:
    if event == "push" and os.environ.get("GITHUB_EVENT_BEFORE", "").strip("0"):
        before = os.environ["GITHUB_EVENT_BEFORE"]
        command = ["git", "diff", "--name-only", f"{before}...HEAD"]
    elif base:
        command = ["git", "diff", "--name-only", f"{base}...HEAD"]
    else:
        command = ["git", "diff", "--name-only", "HEAD~1...HEAD"]
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def write_github_output(selected: Mapping[str, bool], dest: Path | None = None) -> None:
    target = dest
    if target is None:
        raw = os.environ.get("GITHUB_OUTPUT")
        if not raw:
            return
        target = Path(raw)
    lines = [f"{name}={str(value).lower()}\n" for name, value in selected.items()]
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.writelines(lines)


def evaluate_gate(needs: Mapping[str, Mapping[str, str]], selected: Mapping[str, bool]) -> bool:
    if "changes" in needs and str(needs["changes"].get("result", "failure")) != "success":
        return False
    for name in (*PATH_JOBS, *ALWAYS_JOBS):
        if not selected.get(name, False):
            continue
        result = str(needs.get(name, {}).get("result", "failure"))
        if result != "success":
            return False
    return True


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", default=os.environ.get("GITHUB_EVENT_NAME", "pull_request"))
    parser.add_argument("--base", default=os.environ.get("GITHUB_BASE_REF") or os.environ.get("CI_BASE_REF", ""))
    parser.add_argument("--paths-file", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--gate-needs", type=Path, help="JSON object of GitHub needs results.")
    parser.add_argument(
        "--selected",
        default="",
        help="Comma-separated name=true|false pairs used with --gate-needs.",
    )
    args = parser.parse_args(argv)

    if args.gate_needs:
        needs = json.loads(args.gate_needs.read_text(encoding="utf-8"))
        selected = {}
        for item in [part for part in args.selected.split(",") if part]:
            name, _, value = item.partition("=")
            selected[name] = value.lower() == "true"
        return 0 if evaluate_gate(needs, selected) else 1

    if args.event in {"workflow_dispatch", "schedule"}:
        selected = classify_paths([])
    elif args.paths_file:
        selected = classify_paths(args.paths_file.read_text(encoding="utf-8").splitlines())
    else:
        base = args.base
        if base and not base.startswith("origin/") and args.event == "pull_request":
            base = f"origin/{base}"
        selected = classify_paths(changed_files(base or None, args.event))

    write_github_output(selected)
    if args.json:
        json.dump(selected, sys.stdout)
        sys.stdout.write("\n")
    else:
        for name, value in selected.items():
            print(f"{name}={str(value).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
