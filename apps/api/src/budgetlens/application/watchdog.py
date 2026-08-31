from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from budgetlens.adapters.persistence.finance_repositories import (
    SqlImportJobRepository,
    list_stale_processing,
)
from budgetlens.adapters.persistence.repositories import SqlAuditRepository
from budgetlens.application.audit import record_audit
from budgetlens.config import Settings
from budgetlens.domain.identities import Clock, IdFactory
from budgetlens.observability import metrics_registry


def timeout_stale_jobs(
    session: Session,
    *,
    clock: Clock,
    ids: IdFactory,
    settings: Settings,
    trace_id: str = "watchdog",
) -> int:
    cutoff = clock.now() - timedelta(seconds=settings.job_timeout_seconds)
    stale = list_stale_processing(session, cutoff=cutoff)
    audits = SqlAuditRepository(session)
    for job in stale:
        updated = job.mark_timed_out(now=clock.now())
        SqlImportJobRepository(session, job.organization_id).save(updated)
        record_audit(
            audits,
            clock=clock,
            ids=ids,
            organization_id=job.organization_id,
            actor_id=job.created_by,
            action="import.timeout",
            resource_type="import_job",
            resource_id=job.id,
            trace_id=job.trace_id or trace_id,
            metadata={"failure_code": "JOB_TIMEOUT"},
            outcome="failed",
        )
        metrics_registry().record_job_status("failed", timed_out=True)
    return len(stale)
