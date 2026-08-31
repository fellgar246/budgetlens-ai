from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from budgetlens.domain.enums import ImportJobStatus, ScenarioType
from budgetlens.domain.errors import ConflictError, ValidationError
from budgetlens.domain.exporting import render_csv
from budgetlens.domain.importing import ImportJob, propose_mapping, validate_mapping
from budgetlens.domain.text_safety import neutralize_csv_text


def test_mapping_requires_canonical_fields() -> None:
    with pytest.raises(ValidationError) as exc:
        validate_mapping({"period": "Month", "amount": "Actual"})
    assert exc.value.code == "MISSING_COLUMN"


def test_mapping_rejects_duplicate_source_columns() -> None:
    with pytest.raises(ValidationError) as exc:
        validate_mapping(
            {
                "period": "Col",
                "account_code": "Col",
                "department_code": "Dept",
                "amount": "Amt",
                "currency": "Cur",
            }
        )
    assert exc.value.code == "DUPLICATE_COLUMN"


def test_propose_mapping_recognizes_aliases() -> None:
    proposed = propose_mapping(["Month", "Account", "Department", "Actual", "Currency"])
    assert proposed["period"] == "Month"
    assert proposed["account_code"] == "Account"
    assert proposed["amount"] == "Actual"


def test_import_job_rejects_commit_before_ready() -> None:
    job = ImportJob(
        id=UUID(int=1),
        organization_id=UUID(int=2),
        created_by=UUID(int=3),
        import_type=ScenarioType.ACTUAL,
        budget_version_id=None,
        status=ImportJobStatus.CREATED,
        original_filename="a.csv",
        object_key=None,
        sha256="a" * 64,
        size_bytes=10,
        media_type="text/csv",
        template_version="1.0",
        mapping_json={},
        row_count=0,
        valid_count=0,
        error_count=0,
        warning_count=0,
        period_min=None,
        period_max=None,
        valid_amount_total="0.0000",
        idempotency_fingerprint=None,
        started_at=None,
        completed_at=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        failure_code=None,
        create_missing_dimensions=False,
        sheet_name=None,
    )
    with pytest.raises(ConflictError):
        job.assert_committable()


def test_csv_injection_is_neutralized() -> None:
    assert neutralize_csv_text("=1+1") == "'=1+1"
    content = render_csv(("code",), [("=cmd",)]).decode("utf-8")
    assert "'=cmd" in content
