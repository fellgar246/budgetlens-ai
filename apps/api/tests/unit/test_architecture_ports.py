from __future__ import annotations

from pathlib import Path

FORBIDDEN_AWS = ("boto3", "botocore", "aiobotocore", "aioboto3")
FORBIDDEN_APP_ADAPTERS = (
    "budgetlens.adapters.storage",
    "budgetlens.adapters.ai",
    "budgetlens.adapters.identity",
    "budgetlens.adapters.factory",
    "budgetlens.adapters.imports",
    "budgetlens.adapters.parsing",
)
ROOT = Path(__file__).resolve().parents[2] / "src" / "budgetlens"


def _offenders(folder: str, needles: tuple[str, ...]) -> list[str]:
    found: list[str] = []
    for path in (ROOT / folder).rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for name in needles:
            if f"import {name}" in text or f"from {name}" in text:
                found.append(f"{path.relative_to(ROOT)}: {name}")
    return found


def test_domain_and_application_do_not_import_aws() -> None:
    offenders: list[str] = []
    for folder in ("domain", "application", "ports"):
        offenders.extend(_offenders(folder, FORBIDDEN_AWS))
    assert offenders == []


def test_domain_does_not_import_adapters_or_presentation() -> None:
    offenders = _offenders("domain", ("budgetlens.adapters", "budgetlens.presentation", "fastapi"))
    assert offenders == []


def test_application_uses_ports_for_external_systems() -> None:
    offenders = _offenders("application", FORBIDDEN_APP_ADAPTERS + ("fastapi",))
    assert offenders == []


def test_ports_package_has_no_adapter_imports() -> None:
    offenders = _offenders("ports", ("budgetlens.adapters", "fastapi", "sqlalchemy"))
    assert offenders == []


def test_ports_package_exists() -> None:
    expected = {
        "ai.py",
        "clock.py",
        "identity.py",
        "imports.py",
        "parsing.py",
        "storage.py",
        "telemetry.py",
    }
    present = {path.name for path in (ROOT / "ports").glob("*.py")}
    assert expected <= present
