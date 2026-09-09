from __future__ import annotations

import re
from pathlib import Path

from budgetlens.adapters.persistence.models import FinancialEntryRow
from budgetlens.config import Settings
from budgetlens.ports.exports import ExportExecutor
from budgetlens.ports.imports import ImportExecutor

REPO_ROOT = Path(__file__).resolve().parents[4]
API_SRC = REPO_ROOT / "apps" / "api" / "src" / "budgetlens"
WEB_SRC = REPO_ROOT / "apps" / "web" / "src"


def _settings(**overrides: object) -> Settings:
    payload: dict[str, object] = {
        "app_env": "test",
        "database_url": "postgresql+psycopg://budgetlens:x@localhost:5432/budgetlens",
    }
    payload.update(overrides)
    return Settings.model_validate(payload)


def test_worker_reuses_the_api_package() -> None:
    entrypoint = (REPO_ROOT / "apps" / "api" / "docker-entrypoint.sh").read_text(encoding="utf-8")
    assert "python -m budgetlens" in entrypoint
    assert "import-job" in entrypoint
    assert "worker)" in entrypoint
    cli = (API_SRC / "cli.py").read_text(encoding="utf-8")
    assert "import-job" in cli
    assert "run_worker_loop" in cli
    assert "budgetlens.application.imports" in cli


def test_domain_modules_do_not_call_each_other_over_http() -> None:
    offenders: list[str] = []
    needles = ("import requests", "import httpx", "from requests", "from httpx")
    for folder in ("domain", "application"):
        for path in (API_SRC / folder).rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if any(needle in text for needle in needles):
                offenders.append(str(path.relative_to(API_SRC)))
    assert offenders == []


def test_money_column_is_numeric_19_4() -> None:
    column = FinancialEntryRow.__table__.c.amount.type
    assert getattr(column, "precision", None) == 19
    assert getattr(column, "scale", None) == 4


def test_web_is_static_export_without_ssr_hooks() -> None:
    config = (REPO_ROOT / "apps" / "web" / "next.config.ts").read_text(encoding="utf-8")
    assert 'output: "export"' in config
    offenders: list[str] = []
    forbidden = ("getServerSideProps", "cookies(", "headers(", "unstable_noStore")
    for path in WEB_SRC.rglob("*.tsx"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in text:
                offenders.append(f"{path.relative_to(WEB_SRC)}: {token}")
    assert offenders == []


def test_terraform_pin_supports_native_s3_lockfile() -> None:
    raw = (
        (REPO_ROOT / "infrastructure" / "terraform" / ".terraform-version")
        .read_text(encoding="utf-8")
        .strip()
    )
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", raw)
    assert match is not None
    version = tuple(int(part) for part in match.groups())
    assert version >= (1, 10, 0)
    tree = REPO_ROOT / "infrastructure" / "terraform"
    dynamo_hits = [
        str(path.relative_to(REPO_ROOT))
        for path in tree.rglob("*.tf")
        if "aws_dynamodb_table" in path.read_text(encoding="utf-8")
        or "dynamodb_table" in path.read_text(encoding="utf-8")
    ]
    assert dynamo_hits == []
    readme = (tree / "README.md").read_text(encoding="utf-8")
    assert "use_lockfile" in readme


def test_github_workflows_do_not_store_aws_access_keys() -> None:
    github = REPO_ROOT / ".github"
    offenders: list[str] = []
    for path in github.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if "AWS_ACCESS_KEY_ID" in text or "AWS_SECRET_ACCESS_KEY" in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == []


def test_import_executor_port_is_swappable() -> None:
    assert hasattr(ImportExecutor, "run")
    assert _settings().import_executor == "inline"
    assert _settings(import_executor="process").import_executor == "process"


def test_export_executor_port_is_swappable() -> None:
    assert hasattr(ExportExecutor, "run")
    assert _settings().export_executor == "inline"
    assert _settings(export_executor="process").export_executor == "process"


def test_copilot_persists_through_the_content_policy() -> None:
    text = (API_SRC / "application" / "ai.py").read_text(encoding="utf-8")
    assert "persistable_message_content" in text


def test_production_forces_redacted_conversation_content() -> None:
    local = _settings(app_env="local")
    assert local.conversation_content_mode == "full_synthetic"
    prod = _settings(
        app_env="prod",
        auth_mode="oidc",
        oidc_issuer="https://cognito.example/pool",
        oidc_audience="web-client",
        oidc_jwks_url="https://cognito.example/jwks",
        conversation_content_mode="full_synthetic",
        storage_key_pepper="prod-pepper-from-secrets-manager",
    )
    assert prod.conversation_content_mode == "redacted"
