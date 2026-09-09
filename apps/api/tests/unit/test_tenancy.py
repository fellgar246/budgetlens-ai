from __future__ import annotations

from uuid import UUID

import pytest

from budgetlens.adapters.persistence.repositories import SqlAccountRepository
from budgetlens.adapters.tenancy import apply_runtime_role, require_tenant_id
from budgetlens.domain.errors import PermissionDeniedError


class _MissingRoleSession:
    def execute(self, statement: object, params: object | None = None) -> object:
        del statement, params

        class _Result:
            def scalar(self) -> None:
                return None

        return _Result()


class _SetRoleSession:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def execute(self, statement: object, params: object | None = None) -> object:
        sql = str(getattr(statement, "text", statement))
        self.statements.append(sql)
        if "pg_roles" in sql:

            class _Result:
                def scalar(self) -> int:
                    return 1

            return _Result()
        return None


def test_require_tenant_id_rejects_a_missing_organization() -> None:
    with pytest.raises(PermissionDeniedError):
        require_tenant_id(None)
    assert require_tenant_id(UUID(int=3)) == UUID(int=3)


def test_tenant_repository_rejects_a_missing_organization() -> None:
    with pytest.raises(PermissionDeniedError):
        SqlAccountRepository(object(), None)  # type: ignore[arg-type]


def test_runtime_role_missing_fails_closed_outside_local_test() -> None:
    apply_runtime_role(_MissingRoleSession(), "budgetlens_app", app_env="local")  # type: ignore[arg-type]
    apply_runtime_role(_MissingRoleSession(), "budgetlens_app", app_env="test")  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="DATABASE_RUNTIME_ROLE"):
        apply_runtime_role(_MissingRoleSession(), "budgetlens_app", app_env="prod")  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="DATABASE_RUNTIME_ROLE"):
        apply_runtime_role(_MissingRoleSession(), "budgetlens_app", app_env="dev")  # type: ignore[arg-type]


def test_runtime_role_is_applied_when_present() -> None:
    session = _SetRoleSession()
    apply_runtime_role(session, "budgetlens_app", app_env="prod")  # type: ignore[arg-type]
    assert any("SET LOCAL ROLE budgetlens_app" in item for item in session.statements)


def test_runtime_role_rejects_unsafe_identifiers() -> None:
    with pytest.raises(ValueError):
        apply_runtime_role(_MissingRoleSession(), "budgetlens-app; DROP ROLE", app_env="local")  # type: ignore[arg-type]
