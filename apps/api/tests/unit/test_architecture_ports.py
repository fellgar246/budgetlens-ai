from __future__ import annotations

from pathlib import Path

FORBIDDEN_AWS = ("boto3", "botocore", "aiobotocore", "aioboto3")
FORBIDDEN_IDENTITY_SDKS = ("jose", "jwt", "cognito", "authlib")
FORBIDDEN_DOMAIN = (
    *FORBIDDEN_AWS,
    *FORBIDDEN_IDENTITY_SDKS,
    "fastapi",
    "sqlalchemy",
    "budgetlens.adapters",
    "budgetlens.presentation",
)
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


def test_domain_does_not_import_frameworks_or_adapters() -> None:
    offenders = _offenders("domain", FORBIDDEN_DOMAIN)
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


def test_http_routes_do_not_contain_sql() -> None:
    offenders: list[str] = []
    needles = ("from sqlalchemy", "import sqlalchemy", "select(", "text(")
    for path in (ROOT / "presentation" / "routes").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for name in needles:
            if name in text:
                offenders.append(f"{path.relative_to(ROOT)}: {name}")
    assert offenders == []


def test_repositories_do_not_decide_authorization() -> None:
    offenders: list[str] = []
    import_needles = (
        "budgetlens.domain.permissions",
        "budgetlens.adapters.identity",
        "budgetlens.ports.identity",
    )
    persistence = ROOT / "adapters" / "persistence"
    for path in persistence.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for name in import_needles:
            if f"import {name}" in text or f"from {name}" in text:
                offenders.append(f"{path.relative_to(ROOT)}: {name}")
        if "require_permission" in text:
            offenders.append(f"{path.relative_to(ROOT)}: require_permission")
    assert offenders == []


def test_domain_errors_are_translated_only_in_presentation() -> None:
    offenders: list[str] = []
    for path in ROOT.rglob("*.py"):
        if path.name == "errors.py" and path.parent.name == "presentation":
            continue
        if "add_exception_handler" in path.read_text(encoding="utf-8"):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
