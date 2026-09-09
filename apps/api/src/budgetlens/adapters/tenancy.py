from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from budgetlens.domain.errors import PermissionDeniedError

_ROLE_RE = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


def require_tenant_id(organization_id: UUID | None) -> UUID:
    if organization_id is None:
        raise PermissionDeniedError("Selecciona una organización válida.")
    return organization_id


def apply_runtime_role(session: Session, role: str, *, app_env: str = "local") -> None:
    if not role:
        return
    if _ROLE_RE.fullmatch(role) is None:
        raise ValueError("DATABASE_RUNTIME_ROLE is not a valid PostgreSQL identifier")
    exists = session.execute(
        text("SELECT 1 FROM pg_roles WHERE rolname = :role"),
        {"role": role},
    ).scalar()
    if exists is None:
        if app_env not in {"local", "test"}:
            raise RuntimeError("DATABASE_RUNTIME_ROLE is not available")
        return
    session.execute(text(f"SET LOCAL ROLE {role}"))


def apply_tenant_gucs(
    session: Session,
    *,
    user_id: UUID | None = None,
    organization_id: UUID | None = None,
) -> None:
    if user_id is not None:
        session.execute(
            text("SELECT set_config('app.user_id', :value, true)"),
            {"value": str(user_id)},
        )
    if organization_id is not None:
        session.execute(
            text("SELECT set_config('app.organization_id', :value, true)"),
            {"value": str(organization_id)},
        )
