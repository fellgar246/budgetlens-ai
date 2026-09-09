from __future__ import annotations

import hashlib
import hmac
import importlib
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol, cast
from uuid import UUID, uuid4

from budgetlens.application.resilience import (
    CircuitBreaker,
    RetryPolicy,
    retry_with_jitter,
    storage_circuit,
)
from budgetlens.domain.errors import (
    CircuitOpenError,
    DependencyUnavailableError,
    NotFoundError,
    ValidationError,
    storage_unavailable,
)
from budgetlens.domain.text_safety import sanitize_filename
from budgetlens.ports.storage import ObjectStorage, PresignedObject

__all__ = [
    "LocalObjectStorage",
    "ObjectStorage",
    "PresignedObject",
    "S3ObjectStorage",
    "object_key",
    "require_tenant_object_key",
    "tenant_prefix",
]

DEFAULT_KEY_PEPPER = "budgetlens-local-storage-pepper"


class _S3Client(Protocol):
    def put_object(self, **kwargs: Any) -> Any: ...

    def get_object(self, **kwargs: Any) -> Any: ...

    def delete_object(self, **kwargs: Any) -> Any: ...

    def head_object(self, **kwargs: Any) -> Any: ...

    def generate_presigned_url(
        self, ClientMethod: str, Params: dict[str, Any], ExpiresIn: int = 900
    ) -> str: ...


def tenant_prefix(organization_id: UUID, pepper: str) -> str:
    return hmac.new(
        pepper.encode("utf-8"),
        str(organization_id).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:32]


def object_key(
    *,
    organization_id: UUID,
    namespace: str,
    name: str,
    pepper: str = DEFAULT_KEY_PEPPER,
) -> str:
    safe_name = sanitize_filename(name)
    return f"{tenant_prefix(organization_id, pepper)}/{namespace}/{uuid4().hex}/{safe_name}"


def assert_safe_key(key: str) -> str:
    if key.startswith("/") or ".." in Path(key).parts:
        raise ValidationError("INVALID_OBJECT_KEY", "La clave de almacenamiento no es válida.")
    return key


def key_belongs_to_organization(key: str, organization_id: UUID, pepper: str) -> bool:
    return assert_safe_key(key).startswith(f"{tenant_prefix(organization_id, pepper)}/")


def require_tenant_object_key(key: str, organization_id: UUID, pepper: str) -> str:
    cleaned = assert_safe_key(key)
    if not key_belongs_to_organization(cleaned, organization_id, pepper):
        raise NotFoundError("No se encontró el archivo.")
    return cleaned


class LocalObjectStorage:
    def __init__(self, root: str, *, key_pepper: str = DEFAULT_KEY_PEPPER) -> None:
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._key_pepper = key_pepper

    def generate_key(self, *, organization_id: UUID, namespace: str, name: str) -> str:
        return object_key(
            organization_id=organization_id,
            namespace=namespace,
            name=name,
            pepper=self._key_pepper,
        )

    def assert_tenant_key(self, key: str, *, organization_id: UUID) -> None:
        require_tenant_object_key(key, organization_id, self._key_pepper)

    def _path(self, key: str) -> Path:
        path = (self._root / assert_safe_key(key)).resolve()
        if not str(path).startswith(str(self._root)):
            raise ValidationError("INVALID_OBJECT_KEY", "La clave de almacenamiento no es válida.")
        return path

    def put(self, key: str, data: bytes, *, content_type: str) -> None:
        del content_type
        try:
            path = self._path(key)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        except ValidationError:
            raise
        except OSError as exc:
            raise storage_unavailable() from exc

    def get(self, key: str) -> bytes:
        try:
            path = self._path(key)
            if not path.is_file():
                raise NotFoundError("No se encontró el archivo.")
            return path.read_bytes()
        except (NotFoundError, ValidationError):
            raise
        except OSError as exc:
            raise storage_unavailable() from exc

    def exists(self, key: str) -> bool:
        try:
            return self._path(key).is_file()
        except ValidationError:
            raise
        except OSError as exc:
            raise storage_unavailable() from exc

    def delete(self, key: str) -> None:
        try:
            path = self._path(key)
            if path.is_file():
                path.unlink()
        except ValidationError:
            raise
        except OSError as exc:
            raise storage_unavailable() from exc

    def presign_put(
        self,
        key: str,
        *,
        organization_id: UUID,
        content_type: str,
        expires_in: int = 900,
    ) -> PresignedObject | None:
        del content_type, expires_in
        require_tenant_object_key(key, organization_id, self._key_pepper)
        return None

    def presign_get(
        self,
        key: str,
        *,
        organization_id: UUID,
        expires_in: int = 900,
    ) -> PresignedObject | None:
        del expires_in
        require_tenant_object_key(key, organization_id, self._key_pepper)
        return None


class S3ObjectStorage:
    def __init__(
        self,
        *,
        bucket: str,
        region: str,
        prefix: str = "",
        endpoint_url: str = "",
        client: _S3Client | None = None,
        key_pepper: str = DEFAULT_KEY_PEPPER,
        retry: RetryPolicy | None = None,
        circuit: CircuitBreaker | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self._bucket = bucket.strip()
        self._region = region
        self._prefix = prefix.strip().strip("/")
        self._endpoint_url = endpoint_url.strip()
        self._client = client
        self._key_pepper = key_pepper
        self._retry = retry or RetryPolicy()
        self._circuit = circuit or storage_circuit()
        self._sleeper = sleeper

    def generate_key(self, *, organization_id: UUID, namespace: str, name: str) -> str:
        return object_key(
            organization_id=organization_id,
            namespace=namespace,
            name=name,
            pepper=self._key_pepper,
        )

    def assert_tenant_key(self, key: str, *, organization_id: UUID) -> None:
        require_tenant_object_key(key, organization_id, self._key_pepper)

    def _object_key(self, key: str) -> str:
        cleaned = assert_safe_key(key)
        if not self._prefix:
            return cleaned
        return f"{self._prefix}/{cleaned}"

    def _require_client(self) -> _S3Client:
        if self._client is not None:
            return self._client
        if not self._bucket:
            raise storage_unavailable()
        kwargs: dict[str, str] = {"region_name": self._region}
        if self._endpoint_url:
            kwargs["endpoint_url"] = self._endpoint_url
        self._client = cast(_S3Client, _boto3_client("s3", **kwargs))
        return self._client

    def _run[T](self, operation: Callable[[], T]) -> T:
        def once() -> T:
            try:
                return operation()
            except (NotFoundError, ValidationError, CircuitOpenError, DependencyUnavailableError):
                raise
            except Exception as exc:
                if _is_missing_object(exc):
                    raise NotFoundError("No se encontró el archivo.") from exc
                raise

        try:
            return self._circuit.call(
                lambda: retry_with_jitter(
                    once,
                    policy=self._retry,
                    sleeper=self._sleeper,
                )
            )
        except (NotFoundError, ValidationError, CircuitOpenError, DependencyUnavailableError):
            raise
        except Exception as exc:
            raise storage_unavailable() from exc

    def put(self, key: str, data: bytes, *, content_type: str) -> None:
        def write() -> None:
            self._require_client().put_object(
                Bucket=self._bucket,
                Key=self._object_key(key),
                Body=data,
                ContentType=content_type or "application/octet-stream",
                ServerSideEncryption="AES256",
            )

        self._run(write)

    def get(self, key: str) -> bytes:
        def read() -> bytes:
            response = self._require_client().get_object(
                Bucket=self._bucket, Key=self._object_key(key)
            )
            body = response["Body"].read()
            if not isinstance(body, bytes):
                raise storage_unavailable()
            return body

        return self._run(read)

    def exists(self, key: str) -> bool:
        def head() -> bool:
            try:
                self._require_client().head_object(Bucket=self._bucket, Key=self._object_key(key))
            except Exception as exc:
                if _is_missing_object(exc):
                    return False
                raise
            return True

        return self._run(head)

    def delete(self, key: str) -> None:
        def remove() -> None:
            self._require_client().delete_object(Bucket=self._bucket, Key=self._object_key(key))

        try:
            self._run(remove)
        except NotFoundError:
            return

    def presign_put(
        self,
        key: str,
        *,
        organization_id: UUID,
        content_type: str,
        expires_in: int = 900,
    ) -> PresignedObject | None:
        require_tenant_object_key(key, organization_id, self._key_pepper)
        return self._presign(
            "put_object",
            key,
            expires_in=expires_in,
            extra={"ContentType": content_type or "application/octet-stream"},
        )

    def presign_get(
        self,
        key: str,
        *,
        organization_id: UUID,
        expires_in: int = 900,
    ) -> PresignedObject | None:
        require_tenant_object_key(key, organization_id, self._key_pepper)
        return self._presign("get_object", key, expires_in=expires_in)

    def _presign(
        self,
        method: str,
        key: str,
        *,
        expires_in: int,
        extra: dict[str, str] | None = None,
    ) -> PresignedObject:
        params: dict[str, Any] = {"Bucket": self._bucket, "Key": self._object_key(key)}
        if extra:
            params.update(extra)
        try:
            url = self._run(
                lambda: self._require_client().generate_presigned_url(
                    method, Params=params, ExpiresIn=expires_in
                )
            )
        except (NotFoundError, ValidationError, CircuitOpenError, DependencyUnavailableError):
            raise
        except Exception as exc:
            raise storage_unavailable() from exc
        if not url:
            raise storage_unavailable()
        http_method = "PUT" if method == "put_object" else "GET"
        return PresignedObject(method=http_method, url=url, expires_in=expires_in)


def _is_missing_object(exc: Exception) -> bool:
    payload = getattr(exc, "response", None)
    if not isinstance(payload, dict):
        return type(exc).__name__ in {"NoSuchKey", "NotFound"}
    error = cast(dict[str, object], payload).get("Error")
    if not isinstance(error, dict):
        return False
    code = cast(dict[str, object], error).get("Code")
    return code in {"404", "NoSuchKey", "NotFound"}


def _boto3_client(service: str, **kwargs: object) -> object:
    try:
        module = importlib.import_module("boto3")
    except ImportError as exc:
        raise storage_unavailable() from exc
    factory = getattr(module, "client", None)
    if not callable(factory):
        raise storage_unavailable()
    return factory(service, **kwargs)
