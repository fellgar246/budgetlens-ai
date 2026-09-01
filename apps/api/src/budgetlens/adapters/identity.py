from __future__ import annotations

from uuid import UUID

from budgetlens.adapters.oidc import JwksCache, decode_and_validate_token
from budgetlens.adapters.persistence.repositories import SqlUserRepository
from budgetlens.config import Settings
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
    def __init__(
        self,
        users: SqlUserRepository | None = None,
        settings: Settings | None = None,
        *,
        jwks: JwksCache | None = None,
    ) -> None:
        self._users = users
        self._settings = settings
        self._jwks = jwks

    def authenticate(self, token: str) -> User:
        settings = self._settings
        if (
            settings is None
            or self._users is None
            or not settings.oidc_issuer
            or not settings.oidc_audience
            or not (settings.oidc_jwks_url or self._jwks is not None)
        ):
            raise UnauthenticatedError("La autenticación no está disponible en este entorno.")
        jwks = self._jwks or JwksCache(
            settings.oidc_jwks_url,
            ttl_seconds=settings.oidc_jwks_cache_seconds,
        )
        claims = decode_and_validate_token(
            token,
            issuer=settings.oidc_issuer,
            audience=settings.oidc_audience,
            jwks=jwks,
        )
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            raise UnauthenticatedError()
        user = self._users.get_by_external_subject(subject.strip())
        if user is None:
            raise UnauthenticatedError()
        user.assert_active()
        return user


def build_identity_provider(
    *,
    auth_mode: str,
    app_env: str,
    users: SqlUserRepository,
    settings: Settings | None = None,
) -> IdentityProvider:
    if auth_mode == "dev" and app_env in {"local", "test"}:
        return DevIdentityAdapter(users)
    return OidcIdentityAdapter(users, settings)
