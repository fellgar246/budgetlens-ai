from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from budgetlens.adapters.persistence.finance_repositories import (
    SqlConversationRepository,
    SqlExportJobRepository,
    SqlImportErrorRepository,
    SqlImportJobRepository,
    list_expired_conversations,
    list_expired_exports,
    list_jobs_with_expired_error_reports,
    list_jobs_with_expired_originals,
)
from budgetlens.config import Settings
from budgetlens.domain.identities import Clock
from budgetlens.ports.storage import ObjectStorage


def purge_expired_originals(
    session: Session,
    storage: ObjectStorage,
    *,
    clock: Clock,
    settings: Settings,
) -> int:
    cutoff = clock.now() - timedelta(days=settings.original_file_retention_days)
    expired = list_jobs_with_expired_originals(session, cutoff=cutoff)
    purged = 0
    for job in expired:
        if job.object_key:
            storage.delete(job.object_key)
        SqlImportJobRepository(session, job.organization_id).save(job.clear_object_key())
        purged += 1
    return purged


def purge_expired_error_reports(
    session: Session,
    *,
    clock: Clock,
    settings: Settings,
) -> int:
    cutoff = clock.now() - timedelta(days=settings.error_report_retention_days)
    expired = list_jobs_with_expired_error_reports(session, cutoff=cutoff)
    purged = 0
    for job in expired:
        SqlImportErrorRepository(session, job.organization_id).delete_for_job(job.id)
        purged += 1
    return purged


def purge_expired_exports(
    session: Session,
    storage: ObjectStorage,
    *,
    clock: Clock,
) -> int:
    expired = list_expired_exports(session, now=clock.now())
    purged = 0
    for job in expired:
        if job.object_key:
            storage.delete(job.object_key)
        SqlExportJobRepository(session, job.organization_id).save(job.mark_expired())
        purged += 1
    return purged


def purge_expired_conversations(session: Session, *, clock: Clock) -> int:
    expired = list_expired_conversations(session, now=clock.now())
    purged = 0
    now = clock.now()
    for conversation in expired:
        updated = conversation.soft_delete(now=now)
        SqlConversationRepository(session, conversation.organization_id).save(updated)
        purged += 1
    return purged
