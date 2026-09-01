from __future__ import annotations

from uuid import UUID

from budgetlens.adapters.persistence.repositories import SqlUserRepository
from budgetlens.domain.errors import UnauthenticatedError
from budgetlens.domain.organization import User
from budgetlens.ports.identity import IdentityProvider


class DevIdentityAdapter:
    def __init__(self, users: SqlUserRepository) -> None:
        self._users = users

    def authenticate(self, token: str) -> User:
        cleaned = token.removeprefix("dev/") if token.startswith("dev/") else token
        try:
            user_id = UUID(cleaned)
        except ValueError as exc:
            raise UnauthenticatedError() from exc
        user = self._users.get(user_id)
        if user is None:
            raise UnauthenticatedError()
        user.assert_active()
        return user


class OidcIdentityAdapter:
    def authenticate(self, token: str) -> User:
        del token
        raise UnauthenticatedError("La autenticación no está disponible en este entorno.")


def build_identity_provider(
    *, auth_mode: str, app_env: str, users: SqlUserRepository
) -> IdentityProvider:
    if auth_mode == "dev" and app_env in {"local", "test"}:
        return DevIdentityAdapter(users)
    return OidcIdentityAdapter()
