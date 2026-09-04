from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from budgetlens.domain.enums import ImportErrorSeverity, ImportJobStatus, ScenarioType
from budgetlens.domain.errors import ConflictError, ValidationError
from budgetlens.domain.exporting import export_filename, render_csv
from budgetlens.domain.importing import (
    ImportIssue,
    ImportJob,
    abbreviated_sha256,
    group_import_issues,
    propose_mapping,
    validate_mapping,
)
from budgetlens.domain.text_safety import neutralize_csv_text, sanitize_filename


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


def test_processing_job_can_timeout() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    job = ImportJob(
        id=UUID(int=1),
        organization_id=UUID(int=2),
        created_by=UUID(int=3),
        import_type=ScenarioType.ACTUAL,
        budget_version_id=None,
        status=ImportJobStatus.CREATED,
        original_filename="a.csv",
        object_key="org/a.csv",
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
        created_at=now,
        failure_code=None,
        create_missing_dimensions=False,
        sheet_name=None,
    )
    uploaded = job.mark_uploaded(object_key="org/a.csv", media_type="text/csv", now=now)
    processing = uploaded.mark_processing(now=now, trace_id="trace-1")
    assert processing.status is ImportJobStatus.PROCESSING
    assert processing.trace_id == "trace-1"
    timed = processing.mark_timed_out(now=now)
    assert timed.status is ImportJobStatus.FAILED
    assert timed.failure_code == "JOB_TIMEOUT"


def test_original_filename_is_sanitized_for_presentation() -> None:
    assert sanitize_filename("../../etc/passwd.csv") == "passwd.csv"
    assert sanitize_filename("=cmd.xlsx") == "cmd.xlsx"
    assert sanitize_filename("") == "upload.bin"


def test_csv_injection_is_neutralized() -> None:
    assert neutralize_csv_text("=1+1") == "'=1+1"
    assert neutralize_csv_text("-100.0000") == "-100.0000"
    content = render_csv(("code",), [("=cmd",)]).decode("utf-8")
    assert "'=cmd" in content
    assert content.startswith("\ufeff")


def test_export_filename_is_safe_and_stable() -> None:
    from datetime import date

    assert (
        export_filename(period_from=date(2026, 1, 1), period_to=date(2026, 6, 1))
        == "budgetlens-variance-2026-01_2026-06.csv"
    )


def test_issues_are_grouped_and_hash_is_abbreviated() -> None:
    issues = [
        ImportIssue(
            row_number=2,
            field="amount",
            code="INVALID_AMOUNT",
            message="El importe no es válido.",
            raw_value_redacted="x",
            severity=ImportErrorSeverity.ERROR,
        ),
        ImportIssue(
            row_number=3,
            field="amount",
            code="INVALID_AMOUNT",
            message="El importe no es válido.",
            raw_value_redacted="y",
            severity=ImportErrorSeverity.ERROR,
        ),
        ImportIssue(
            4,
            "cost_center_code",
            "EMPTY_OPTIONAL_VALUE",
            "Se aplicó Sin asignar.",
            "",
            ImportErrorSeverity.WARNING,
        ),
    ]
    groups = group_import_issues(issues)
    assert groups[0].code == "INVALID_AMOUNT"
    assert groups[0].count == 2
    assert abbreviated_sha256("a" * 64) == "a" * 12


def test_applied_job_cannot_be_reapplied() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    job = ImportJob(
        id=UUID(int=1),
        organization_id=UUID(int=2),
        created_by=UUID(int=3),
        import_type=ScenarioType.ACTUAL,
        budget_version_id=None,
        status=ImportJobStatus.READY,
        original_filename="a.csv",
        object_key="org/a.csv",
        sha256="a" * 64,
        size_bytes=10,
        media_type="text/csv",
        template_version="1.0",
        mapping_json={},
        row_count=1,
        valid_count=1,
        error_count=0,
        warning_count=0,
        period_min=None,
        period_max=None,
        valid_amount_total="10.0000",
        idempotency_fingerprint="b" * 64,
        started_at=now,
        completed_at=None,
        created_at=now,
        failure_code=None,
        create_missing_dimensions=False,
        sheet_name=None,
    )
    applied = job.mark_applied(now=now)
    assert applied.status is ImportJobStatus.APPLIED
    assert applied.mark_applied(now=now) == applied
    with pytest.raises(ConflictError) as committable:
        applied.assert_committable()
    assert committable.value.code == "IMPORT_NOT_READY"
    with pytest.raises(ConflictError) as failed:
        applied.mark_failed(code="RETRY", now=now)
    assert failed.value.code == "IMPORT_STATE"


def test_commit_rejects_hash_change_after_validate() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    job = ImportJob(
        id=UUID(int=1),
        organization_id=UUID(int=2),
        created_by=UUID(int=3),
        import_type=ScenarioType.ACTUAL,
        budget_version_id=None,
        status=ImportJobStatus.READY,
        original_filename="a.csv",
        object_key="org/a.csv",
        sha256="a" * 64,
        size_bytes=10,
        media_type="text/csv",
        template_version="1.0",
        mapping_json={},
        row_count=1,
        valid_count=1,
        error_count=0,
        warning_count=0,
        period_min=None,
        period_max=None,
        valid_amount_total="10.0000",
        idempotency_fingerprint="b" * 64,
        started_at=now,
        completed_at=None,
        created_at=now,
        failure_code=None,
        create_missing_dimensions=False,
        sheet_name=None,
    )
    job.assert_committable()
    with pytest.raises(ConflictError) as mismatch:
        job.assert_same_hash("c" * 64)
    assert mismatch.value.code == "IMPORT_HASH_MISMATCH"
