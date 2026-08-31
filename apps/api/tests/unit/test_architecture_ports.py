from __future__ import annotations

from pathlib import Path

FORBIDDEN = ("boto3", "botocore", "aiobotocore", "aioboto3")
ROOT = Path(__file__).resolve().parents[2] / "src" / "budgetlens"


def test_domain_and_application_do_not_import_aws() -> None:
    offenders: list[str] = []
    for folder in ("domain", "application"):
        for path in (ROOT / folder).rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for name in FORBIDDEN:
                if f"import {name}" in text or f"from {name}" in text:
                    offenders.append(f"{path}: {name}")
    assert offenders == []
