from __future__ import annotations

import json
import time
import urllib.request
from typing import Any, Protocol, cast
from urllib.error import URLError

from budgetlens.domain.errors import UnauthenticatedError


class JwksFetcher(Protocol):
    def __call__(self, url: str) -> dict[str, Any]: ...


class JwksCache:
    def __init__(
        self,
        url: str,
        *,
        ttl_seconds: int = 300,
        fetcher: JwksFetcher | None = None,
    ) -> None:
        self._url = url
        self._ttl_seconds = ttl_seconds
        self._fetcher = fetcher or _fetch_json
        self._expires_at = 0.0
        self._keys: dict[str, dict[str, Any]] = {}

    def get_key(self, kid: str) -> dict[str, Any]:
        now = time.monotonic()
        if now >= self._expires_at:
            self.refresh()
        key = self._keys.get(kid)
        if key is None:
            self.refresh()
            key = self._keys.get(kid)
        if key is None:
            raise UnauthenticatedError()
        return key

    def refresh(self) -> None:
        try:
            payload = self._fetcher(self._url)
        except (OSError, URLError, TimeoutError, ValueError) as exc:
            raise UnauthenticatedError() from exc
        keys = payload.get("keys")
        if not isinstance(keys, list):
            raise UnauthenticatedError()
        mapped: dict[str, dict[str, Any]] = {}
        for raw in cast(list[object], keys):
            if not isinstance(raw, dict):
                continue
            item = cast(dict[str, Any], raw)
            kid = item.get("kid")
            if isinstance(kid, str) and kid:
                mapped[kid] = item
        self._keys = mapped
        self._expires_at = time.monotonic() + self._ttl_seconds


def decode_and_validate_token(
    token: str,
    *,
    issuer: str,
    audience: str,
    jwks: JwksCache,
) -> dict[str, Any]:
    jwt = _load_jwt()
    try:
        header = jwt.get_unverified_header(token)
    except Exception as exc:
        raise UnauthenticatedError() from exc
    kid = header.get("kid")
    if not isinstance(kid, str) or not kid:
        raise UnauthenticatedError()
    key_data = jwks.get_key(kid)
    try:
        key = jwt.PyJWK.from_dict(key_data).key
        claims = jwt.decode(
            token,
            key=key,
            algorithms=["RS256"],
            issuer=issuer.rstrip("/"),
            options={"require": ["exp", "iss", "sub"], "verify_aud": False},
        )
    except Exception as exc:
        raise UnauthenticatedError() from exc
    if not _audience_matches(claims, audience):
        raise UnauthenticatedError()
    token_use = claims.get("token_use")
    if token_use is not None and token_use not in {"id", "access"}:
        raise UnauthenticatedError()
    return cast(dict[str, Any], claims)


def _audience_matches(claims: dict[str, Any], audience: str) -> bool:
    raw_aud = claims.get("aud")
    if isinstance(raw_aud, str) and raw_aud == audience:
        return True
    if isinstance(raw_aud, list) and audience in raw_aud:
        return True
    client_id = claims.get("client_id")
    return isinstance(client_id, str) and client_id == audience


def _fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JWKS payload must be an object")
    return cast(dict[str, Any], payload)


def _load_jwt() -> Any:
    try:
        return __import__("jwt")
    except ImportError as exc:
        raise UnauthenticatedError("La autenticación no está disponible en este entorno.") from exc
