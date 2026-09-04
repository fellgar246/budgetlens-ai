# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from budgetlens.adapters.db import session_scope
from budgetlens.adapters.persistence.models import FinancialEntryRow, ImportJobRow
from budgetlens.config import get_settings
from budgetlens.dev_identities import ALPHA_ANALYST_ID, ALPHA_ORG_ID

PREFIX = "/api/v1"
ROOT = Path(__file__).resolve().parents[4]
SAMPLE = ROOT / "sample-data"
CANONICAL = {
    "period": "period",
    "account_code": "account_code",
    "department_code": "department_code",
    "cost_center_code": "cost_center_code",
    "amount": "amount",
    "currency": "currency",
}


def auth_headers(
    user_id: UUID,
    organization_id: UUID | None = None,
    idempotency: str | None = None,
) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {user_id}"}
    if organization_id is not None:
        headers["X-Organization-Id"] = str(organization_id)
    if idempotency is not None:
        headers["Idempotency-Key"] = idempotency
    return headers


def sample_bytes(name: str) -> bytes:
    return (SAMPLE / name).read_bytes()


def create_budget_version(
    client: TestClient, name: str = "Plan 2026", fiscal_year: int = 2026
) -> str:
    created = client.post(
        f"{PREFIX}/budget-versions",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        json={"name": name, "fiscal_year": fiscal_year},
    )
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


def import_workbook(
    client: TestClient,
    *,
    content: bytes,
    filename: str,
    import_type: str,
    version_id: str | None,
    user: UUID = ALPHA_ANALYST_ID,
    org: UUID = ALPHA_ORG_ID,
    mapping: dict[str, str] | None = None,
    commit: bool = True,
    idempotency: str = "imp-1",
    media_type: str | None = None,
) -> dict[str, Any]:
    digest = hashlib.sha256(content).hexdigest()
    created = client.post(
        f"{PREFIX}/imports",
        headers=auth_headers(user, org),
        json={
            "import_type": import_type,
            "budget_version_id": version_id,
            "original_filename": filename,
            "size_bytes": len(content),
            "sha256": digest,
            "template_version": "1.0",
        },
    )
    assert created.status_code == 201, created.text
    job_id = created.json()["id"]
    uploaded = client.put(
        f"{PREFIX}/imports/{job_id}/content",
        headers={**auth_headers(user, org), "Content-Type": media_type or "text/csv"},
        content=content,
    )
    assert uploaded.status_code == 200, uploaded.text
    validated = client.post(
        f"{PREFIX}/imports/{job_id}/validate",
        headers=auth_headers(user, org),
        json={"mapping": mapping or CANONICAL, "create_missing_dimensions": False},
    )
    assert validated.status_code == 200, validated.text
    if not commit:
        payload = validated.json()
        assert isinstance(payload, dict)
        return {str(key): value for key, value in payload.items()}
    committed = client.post(
        f"{PREFIX}/imports/{job_id}/commit",
        headers=auth_headers(user, org, idempotency),
    )
    body = committed.json()
    assert isinstance(body, dict)
    typed = {str(key): value for key, value in body.items()}
    return typed | {"_status": committed.status_code, "_body": typed}


def entry_count_for_job(job_id: str) -> int:
    with session_scope() as session:
        stmt = (
            select(func.count())
            .select_from(FinancialEntryRow)
            .where(FinancialEntryRow.import_job_id == UUID(job_id))
        )
        return int(session.scalar(stmt) or 0)


def overwrite_job_object(job_id: str, content: bytes) -> None:
    with session_scope() as session:
        row = session.get(ImportJobRow, UUID(job_id))
        assert row is not None
        assert row.object_key
        path = Path(get_settings().local_storage_path) / row.object_key
        path.write_bytes(content)


def account_id(client: TestClient, code: str) -> str:
    accounts = client.get(
        f"{PREFIX}/accounts",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
    )
    for item in accounts.json()["items"]:
        if item["code"] == code:
            return str(item["id"])
    raise AssertionError(code)
