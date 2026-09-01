from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from budgetlens.adapters.persistence.finance_repositories import (
    SqlImportJobRepository,
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
