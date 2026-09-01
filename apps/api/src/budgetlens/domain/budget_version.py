from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID

from budgetlens.domain.enums import BudgetVersionStatus
from budgetlens.domain.errors import ConflictError
from budgetlens.domain.organization import normalize_name


@dataclass(frozen=True, slots=True)
class BudgetVersion:
    id: UUID
    organization_id: UUID
    name: str
    fiscal_year: int
    status: BudgetVersionStatus
    is_active: bool
    published_at: datetime | None
    published_by: UUID | None
    created_at: datetime
    version: int

    def assert_mutable(self) -> None:
        if self.status is not BudgetVersionStatus.DRAFT:
            raise ConflictError(
                "VERSION_NOT_DRAFT",
                "Solo una versión en borrador puede modificarse. "
                "Publica una versión nueva para corregir.",
            )

    def assert_accepts_entries(self) -> None:
        if self.status is not BudgetVersionStatus.DRAFT:
            raise ConflictError(
                "VERSION_NOT_DRAFT",
                "Una versión publicada no recibe nuevas entradas.",
            )

    def with_draft_metadata(self, *, expected_version: int, name: str) -> BudgetVersion:
        if expected_version != self.version:
            from budgetlens.domain.errors import ConcurrencyError

            raise ConcurrencyError()
        self.assert_mutable()
        return replace(
            self,
            name=normalize_name(name, field="name", max_length=160),
            version=self.version + 1,
        )

    def publish(self, *, now: datetime, actor_id: UUID) -> BudgetVersion:
        if self.status is BudgetVersionStatus.PUBLISHED:
            return self
        if self.status is BudgetVersionStatus.ARCHIVED:
            raise ConflictError(
                "VERSION_ARCHIVED",
                "Una versión archivada no se puede publicar.",
            )
        return replace(
            self,
            status=BudgetVersionStatus.PUBLISHED,
            published_at=now,
            published_by=actor_id,
            version=self.version + 1,
        )

    def activate(self) -> BudgetVersion:
        if self.status is not BudgetVersionStatus.PUBLISHED:
            raise ConflictError(
                "VERSION_NOT_PUBLISHED",
                "Solo una versión publicada puede activarse.",
            )
        if self.is_active:
            return self
        return replace(self, is_active=True, version=self.version + 1)

    def deactivate(self) -> BudgetVersion:
        if not self.is_active:
            return self
        return replace(self, is_active=False, version=self.version + 1)

    def archive(self, *, now: datetime) -> BudgetVersion:
        if self.status is BudgetVersionStatus.ARCHIVED:
            return self
        published_at = self.published_at or now
        return replace(
            self,
            status=BudgetVersionStatus.ARCHIVED,
            is_active=False,
            published_at=published_at,
            version=self.version + 1,
        )

    def appears_in_default_list(self) -> bool:
        return self.status is not BudgetVersionStatus.ARCHIVED
