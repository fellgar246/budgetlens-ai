from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from budgetlens.application.retention import purge_expired_conversations, purge_expired_originals
from budgetlens.application.watchdog import timeout_stale_jobs
from budgetlens.config import Settings
from budgetlens.domain.conversation import Conversation
from budgetlens.domain.enums import ImportJobStatus, ScenarioType
from budgetlens.domain.identities import FrozenClock, SequentialIdFactory
from budgetlens.domain.importing import ImportJob


def _job(
    *,
    status: ImportJobStatus,
    started_at: datetime | None,
    created_at: datetime,
    object_key: str | None = "org/imports/a.csv",
) -> ImportJob:
    return ImportJob(
        id=UUID(int=1),
        organization_id=UUID(int=2),
        created_by=UUID(int=3),
        import_type=ScenarioType.ACTUAL,
        budget_version_id=None,
        status=status,
        original_filename="a.csv",
        object_key=object_key,
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
        started_at=started_at,
        completed_at=None,
        created_at=created_at,
        failure_code=None,
        create_missing_dimensions=False,
        sheet_name=None,
        trace_id="trace-job",
    )


def test_processing_job_times_out() -> None:
    now = datetime(2026, 8, 31, tzinfo=UTC)
    job = _job(
        status=ImportJobStatus.UPLOADED,
        started_at=None,
        created_at=now,
    ).mark_processing(now=now - timedelta(minutes=20), trace_id="trace-job")
    timed = job.mark_timed_out(now=now)
    assert timed.status is ImportJobStatus.FAILED
    assert timed.failure_code == "JOB_TIMEOUT"


def test_watchdog_marks_stale_processing_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2026, 8, 31, tzinfo=UTC)
    stale = _job(
        status=ImportJobStatus.PROCESSING,
        started_at=now - timedelta(minutes=20),
        created_at=now - timedelta(minutes=20),
    )
    saved: list[ImportJob] = []

    class Repo:
        def __init__(self, _session: object, _org: object) -> None:
            del _session, _org

        def save(self, job: ImportJob) -> None:
            saved.append(job)

    def list_stale(_session: object, *, cutoff: datetime) -> list[ImportJob]:
        if stale.started_at and stale.started_at <= cutoff:
            return [stale]
        return []

    def unused_audits(_session: object) -> object:
        return object()

    def skip_audit(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(
        "budgetlens.application.watchdog.list_stale_processing",
        list_stale,
    )
    monkeypatch.setattr(
        "budgetlens.application.watchdog.SqlImportJobRepository",
        Repo,
    )
    monkeypatch.setattr(
        "budgetlens.application.watchdog.SqlAuditRepository",
        unused_audits,
    )
    monkeypatch.setattr(
        "budgetlens.application.watchdog.record_audit",
        skip_audit,
    )
    settings = Settings.model_validate(
        {
            "database_url": "postgresql+psycopg://budgetlens:x@localhost:5432/budgetlens",
            "job_timeout_seconds": 600,
        }
    )
    count = timeout_stale_jobs(
        object(),  # type: ignore[arg-type]
        clock=FrozenClock(now),
        ids=SequentialIdFactory(),
        settings=settings,
    )
    assert count == 1
    assert saved[0].status is ImportJobStatus.FAILED
    assert saved[0].failure_code == "JOB_TIMEOUT"


def test_retention_deletes_originals_and_keeps_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2026, 8, 31, tzinfo=UTC)
    job = _job(
        status=ImportJobStatus.APPLIED,
        started_at=now - timedelta(days=100),
        created_at=now - timedelta(days=100),
    )
    deleted: list[str] = []
    saved: list[ImportJob] = []

    class Storage:
        def delete(self, key: str) -> None:
            deleted.append(key)

    class Repo:
        def __init__(self, _session: object, _org: object) -> None:
            del _session, _org

        def save(self, item: ImportJob) -> None:
            saved.append(item)

    def list_expired(_session: object, *, cutoff: datetime) -> list[ImportJob]:
        del cutoff
        return [job]

    monkeypatch.setattr(
        "budgetlens.application.retention.list_jobs_with_expired_originals",
        list_expired,
    )
    monkeypatch.setattr(
        "budgetlens.application.retention.SqlImportJobRepository",
        Repo,
    )
    settings = Settings.model_validate(
        {
            "database_url": "postgresql+psycopg://budgetlens:x@localhost:5432/budgetlens",
            "original_file_retention_days": 90,
        }
    )
    purged = purge_expired_originals(
        object(),  # type: ignore[arg-type]
        Storage(),  # type: ignore[arg-type]
        clock=FrozenClock(now),
        settings=settings,
    )
    assert purged == 1
    assert deleted == ["org/imports/a.csv"]
    assert saved[0].object_key is None
    assert saved[0].id == job.id


def test_expired_conversations_are_soft_deleted(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2026, 8, 31, tzinfo=UTC)
    conversation = Conversation(
        id=UUID(int=9),
        organization_id=UUID(int=2),
        user_id=UUID(int=3),
        title="Consulta",
        context_filters={},
        created_at=now - timedelta(days=120),
        updated_at=now - timedelta(days=120),
        deleted_at=None,
    )
    saved: list[Conversation] = []

    class Repo:
        def __init__(self, _session: object, _org: object) -> None:
            del _session, _org

        def save(self, item: Conversation) -> None:
            saved.append(item)

    monkeypatch.setattr(
        "budgetlens.application.retention.list_expired_conversations",
        lambda _session, *, now: [conversation],
    )
    monkeypatch.setattr(
        "budgetlens.application.retention.SqlConversationRepository",
        Repo,
    )
    purged = purge_expired_conversations(object(), clock=FrozenClock(now))  # type: ignore[arg-type]
    assert purged == 1
    assert saved[0].deleted_at == now
