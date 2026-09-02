#!/usr/bin/env python3
"""Secret-free portfolio release checks. Does not create a SemVer tag."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs"
API_INIT = REPO_ROOT / "apps" / "api" / "src" / "budgetlens" / "__init__.py"
WEB_PACKAGE = REPO_ROOT / "apps" / "web" / "package.json"

REQUIRED_DOCS: tuple[Path, ...] = (
    REPO_ROOT / "README.md",
    DOCS / "ARCHITECTURE.md",
    DOCS / "DEMO.md",
    DOCS / "AI_EVALUATION.md",
    DOCS / "COST.md",
    DOCS / "RELEASE.md",
    DOCS / "DECISIONS.md",
    DOCS / "BACKLOG.md",
    DOCS / "TRACEABILITY.md",
    DOCS / "GATES.md",
    DOCS / "DEPLOYMENT.md",
    DOCS / "OPERATIONS.md",
    REPO_ROOT / "sample-data" / "README.md",
    DOCS / "screenshots" / "README.md",
)

PORTFOLIO_SCAN_DOCS: tuple[str, ...] = (
    "README.md",
    "docs/ARCHITECTURE.md",
    "docs/DEMO.md",
    "docs/AI_EVALUATION.md",
    "docs/COST.md",
    "docs/RELEASE.md",
    "sample-data/README.md",
    "docs/screenshots/README.md",
)

README_TOKENS: tuple[str, ...] = (
    "docs/DEMO.md",
    "docs/ARCHITECTURE.md",
    "docs/AI_EVALUATION.md",
    "docs/COST.md",
    "docs/RELEASE.md",
    "make doctor",
    "make bootstrap",
    "make seed",
    "synthetic",
)

ARCHITECTURE_TOKENS: tuple[str, ...] = (
    "```mermaid",
    "FastAPI",
    "PostgreSQL",
    "CloudFront",
    "ECS Fargate",
    "row-level security",
    "OIDC",
)

DEMO_TOKENS: tuple[str, ...] = (
    "Ana Analyst",
    "Alpha",
    "Pat Dual",
    "Maintenance",
    "Copiloto",
    "sample-data",
    "http://localhost:3000",
)

EVAL_TOKENS: tuple[str, ...] = (
    "2026-09-01",
    "20 / 20",
    "AI-E01",
    "AI-E12",
    "AI-S01",
    "AI-S08",
    "stub",
    "not claimed",
)

COST_TOKENS: tuple[str, ...] = (
    "Do not invent a monthly price",
    "nat_gateway_count",
    "db.t4g.micro",
    "ai_provider",
    "stub",
    "budget alert",
)

RELEASE_TOKENS: tuple[str, ...] = (
    "0.1.0",
    "v1.0.0",
    "blocked",
    "make portfolio-check",
    "M-10",
)

SECRET_RE = re.compile(
    r"(AKIA[0-9A-Z]{16}|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY|"
    r"postgresql(?:\+psycopg)?://[^:\s]+:[^@\s]+@|"
    r"AWS_SECRET_ACCESS_KEY=)",
    re.IGNORECASE,
)
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
VERSION_RE = re.compile(r'__version__\s*=\s*"([^"]+)"')
ACCOUNT_RE = re.compile(r"\b(?!000000000000)\d{12}\b")

CHECKLIST: tuple[str, ...] = (
    "Required product docs exist and stay secret-free",
    "README links the demo, architecture, eval, cost, and release pages",
    "Architecture diagram matches Compose and Terraform modules",
    "Demo uses the synthetic seed only",
    "AI summary publishes stub aggregates, not prompts",
    "Cost page lists Terraform sizes and does not invent a bill",
    "v1.0.0 stays blocked until recorded production gates exist",
    "Relative Markdown links resolve",
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
        "# Portfolio release",
        "",
        "Local demo documentation and evidence. This script does not apply AWS or create a tag.",
        "",
    ]
    for item in CHECKLIST:
        lines.append(f"- [ ] {item}")
    lines.append("")
    return "\n".join(lines)


def application_version(*, repo_root: Path = REPO_ROOT) -> str:
    api_init = repo_root / API_INIT.relative_to(REPO_ROOT)
    match = VERSION_RE.search(api_init.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError("API package version is missing")
    web = json.loads((repo_root / WEB_PACKAGE.relative_to(REPO_ROOT)).read_text(encoding="utf-8"))
    web_version = str(web.get("version") or "")
    api_version = match.group(1)
    if web_version != api_version:
        raise ValueError(f"web version {web_version} does not match API {api_version}")
    return api_version


def missing_docs(*, repo_root: Path = REPO_ROOT) -> list[str]:
    missing: list[str] = []
    for path in REQUIRED_DOCS:
        resolved = repo_root / path.relative_to(REPO_ROOT)
        if not resolved.is_file():
            missing.append(str(path.relative_to(REPO_ROOT)))
    return missing


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def missing_tokens(text: str, tokens: Sequence[str]) -> list[str]:
    return [token for token in tokens if token not in text]


def secret_hits(text: str) -> list[str]:
    return [match.group(0)[:24] for match in SECRET_RE.finditer(text)]


def unexpected_account_ids(text: str) -> list[str]:
    return ACCOUNT_RE.findall(text)


def markdown_targets(text: str) -> list[str]:
    targets: list[str] = []
    for raw in LINK_RE.findall(text):
        target = raw.split()[0].strip("<>")
        if target.startswith(("#", "http://", "https://", "mailto:")):
            continue
        targets.append(target.split("#", 1)[0])
    return targets


def broken_relative_links(path: Path, *, repo_root: Path = REPO_ROOT) -> list[str]:
    broken: list[str] = []
    for target in markdown_targets(_read(path)):
        if not target:
            continue
        resolved = (path.parent / target).resolve()
        try:
            resolved.relative_to(repo_root.resolve())
        except ValueError:
            broken.append(target)
            continue
        if not resolved.exists():
            broken.append(target)
    return broken


def check_documents(*, repo_root: Path = REPO_ROOT) -> list[str]:
    errors: list[str] = []
    missing = missing_docs(repo_root=repo_root)
    if missing:
        errors.append("missing documents: " + ", ".join(missing))
        return errors

    mapping: tuple[tuple[Path, Sequence[str]], ...] = (
        (repo_root / "README.md", README_TOKENS),
        (repo_root / "docs" / "ARCHITECTURE.md", ARCHITECTURE_TOKENS),
        (repo_root / "docs" / "DEMO.md", DEMO_TOKENS),
        (repo_root / "docs" / "AI_EVALUATION.md", EVAL_TOKENS),
        (repo_root / "docs" / "COST.md", COST_TOKENS),
        (repo_root / "docs" / "RELEASE.md", RELEASE_TOKENS),
    )
    for path, tokens in mapping:
        absent = missing_tokens(_read(path), tokens)
        if absent:
            errors.append(f"{path.relative_to(repo_root)} missing: {', '.join(absent)}")

    cost = _read(repo_root / "docs" / "COST.md")
    if re.search(r"monthly_estimate\s*[:=]\s*\d", cost):
        errors.append("COST.md must not store a monthly_estimate figure")
    if "Do not invent" not in cost:
        errors.append("COST.md must refuse invented prices")

    sizes = _load_script("record_cost_estimate").load_environment_sizes("dev", repo_root=repo_root)
    for key in ("nat_gateway_count", "api_desired_count", "db_instance_class", "ai_provider"):
        if str(sizes[key]) not in cost:
            errors.append(f"COST.md is missing Terraform size {key}={sizes[key]}")

    version = application_version(repo_root=repo_root)
    release = _read(repo_root / "docs" / "RELEASE.md")
    if version not in release:
        errors.append(f"RELEASE.md must name application version {version}")
    if version == "1.0.0":
        missing_gates = production_gate_gaps(repo_root=repo_root)
        if missing_gates:
            errors.append("version 1.0.0 is present but production gates are missing")

    return errors


def scan_product_docs(*, repo_root: Path = REPO_ROOT) -> list[str]:
    errors: list[str] = []
    for relative in PORTFOLIO_SCAN_DOCS:
        path = repo_root / relative
        if not path.is_file():
            errors.append(f"missing {relative}")
            continue
        text = _read(path)
        hits = secret_hits(text)
        if hits:
            errors.append(f"{relative} secret-like text: {hits[0]}")
        if ("spec" + "-docs") in text:
            errors.append(f"{relative} cites a specification path")
        accounts = unexpected_account_ids(text)
        if accounts:
            errors.append(f"{relative} has an account-like id")
        broken = broken_relative_links(path, repo_root=repo_root)
        if broken:
            errors.append(f"{relative} broken link: {broken[0]}")
    return errors


def production_gate_gaps(*, repo_root: Path = REPO_ROOT) -> list[str]:
    gates = _load_script("record_gate")
    return list(gates.check_scope("prod", "prod", repo_root=repo_root, ai_provider="stub"))


def refuse_release_tag(*, repo_root: Path = REPO_ROOT) -> None:
    version = application_version(repo_root=repo_root)
    missing = production_gate_gaps(repo_root=repo_root)
    if missing or version != "1.0.0":
        raise ValueError(
            "v1.0.0 is blocked until the application version is 1.0.0 and recorded "
            f"production gates exist. Missing: {', '.join(missing) or 'version ' + version}"
        )


def check_portfolio(*, repo_root: Path = REPO_ROOT) -> list[str]:
    errors = check_documents(repo_root=repo_root)
    errors.extend(scan_product_docs(repo_root=repo_root))
    return errors


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-checklist", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--tag", action="store_true")
    args = parser.parse_args(argv)

    if args.print_checklist:
        sys.stdout.write(render_checklist())
        return 0

    if args.tag:
        try:
            refuse_release_tag()
        except ValueError as error:
            raise SystemExit(str(error)) from error
        raise SystemExit("tag creation is a human git action after gates are recorded")

    if not args.check:
        raise SystemExit("Pass --check, --print-checklist, or --tag")

    errors = check_portfolio()
    if errors:
        for item in errors:
            print(item, file=sys.stderr)
        return 1
    print("portfolio documentation is complete; v1.0.0 remains gated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
