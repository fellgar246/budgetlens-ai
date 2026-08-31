from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from budgetlens.domain.enums import Role
from budgetlens.domain.organization import User


@dataclass(frozen=True, slots=True)
class TenantContext:
    user: User
    organization_id: UUID
    role: Role
    trace_id: str
