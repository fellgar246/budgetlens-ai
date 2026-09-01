from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from budgetlens.adapters.identity import OidcIdentityAdapter
from budgetlens.adapters.oidc import JwksCache, decode_and_validate_token
from budgetlens.config import Settings
from budgetlens.domain.enums import UserStatus
from budgetlens.domain.errors import UnauthenticatedError
from budgetlens.domain.organization import User


def _rsa_pair() -> tuple[Any, dict[str, Any]]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
    assert isinstance(jwk, dict)
    jwk["kid"] = "test-key"
    jwk["use"] = "sig"
    jwk["alg"] = "RS256"
    return key, jwk


def _token(private_key: Any, **claims: Any) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "iss": "https://cognito.example/pool",
        "sub": "cognito-user-1",
        "aud": "web-client",
        "exp": now + timedelta(minutes=5),
        "token_use": "id",
    }
    payload.update(claims)
    if payload.get("aud") is None:
        payload.pop("aud", None)
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "test-key"})


def test_oidc_validates_signature_issuer_audience_and_maps_subject() -> None:
    private_key, jwk = _rsa_pair()
    jwks = JwksCache(
        "https://example.test/jwks",
        fetcher=lambda url: {"keys": [jwk]},
    )
    settings = Settings.model_validate(
        {
            "app_env": "test",
            "auth_mode": "oidc",
            "database_url": "postgresql+psycopg://budgetlens:x@localhost:5432/budgetlens",
            "oidc_issuer": "https://cognito.example/pool",
            "oidc_audience": "web-client",
            "oidc_jwks_url": "https://example.test/jwks",
        }
    )
    now = datetime(2026, 1, 1, tzinfo=UTC)
    user = User(
        id=UUID(int=21),
        email="mapped@example.com",
        display_name="Mapped",
        status=UserStatus.ACTIVE,
        external_subject="cognito-user-1",
        created_at=now,
        updated_at=now,
    )

    class _Users:
        def get_by_external_subject(self, subject: str) -> User | None:
            return user if subject == "cognito-user-1" else None

    adapter = OidcIdentityAdapter(_Users(), settings, jwks=jwks)  # type: ignore[arg-type]
    authenticated = adapter.authenticate(_token(private_key))
    assert authenticated.id == user.id

    with pytest.raises(UnauthenticatedError):
        adapter.authenticate(_token(private_key, iss="https://evil.example"))
    with pytest.raises(UnauthenticatedError):
        adapter.authenticate(_token(private_key, aud="other-client", client_id="other-client"))
    with pytest.raises(UnauthenticatedError):
        adapter.authenticate(_token(private_key, exp=datetime.now(UTC) - timedelta(minutes=1)))


def test_oidc_accepts_access_token_client_id_and_ignores_org_claim() -> None:
    private_key, jwk = _rsa_pair()
    jwks = JwksCache("https://example.test/jwks", fetcher=lambda url: {"keys": [jwk]})
    token = _token(
        private_key,
        aud=None,
        client_id="web-client",
        token_use="access",
        **{"custom:org": "should-be-ignored"},
    )
    claims = decode_and_validate_token(
        token,
        issuer="https://cognito.example/pool",
        audience="web-client",
        jwks=jwks,
    )
    assert claims["sub"] == "cognito-user-1"
    assert claims.get("custom:org") == "should-be-ignored"
