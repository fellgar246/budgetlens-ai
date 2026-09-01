from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Protocol, cast
from uuid import UUID

from budgetlens.domain.errors import NotFoundError, ValidationError, storage_unavailable
from budgetlens.ports.storage import ObjectStorage

__all__ = ["LocalObjectStorage", "ObjectStorage", "S3ObjectStorage"]


class _S3Client(Protocol):
    def put_object(self, **kwargs: Any) -> Any: ...

    def get_object(self, **kwargs: Any) -> Any: ...

    def delete_object(self, **kwargs: Any) -> Any: ...

    def head_object(self, **kwargs: Any) -> Any: ...


def object_key(*, organization_id: UUID, namespace: str, name: str) -> str:
    safe_name = Path(name).name.replace("..", "")
    return f"{organization_id}/{namespace}/{safe_name}"


def assert_safe_key(key: str) -> str:
    if key.startswith("/") or ".." in Path(key).parts:
        raise ValidationError("INVALID_OBJECT_KEY", "La clave de almacenamiento no es válida.")
    return key


class LocalObjectStorage:
    def __init__(self, root: str) -> None:
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def generate_key(self, *, organization_id: UUID, namespace: str, name: str) -> str:
        return object_key(organization_id=organization_id, namespace=namespace, name=name)

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


class S3ObjectStorage:
    def __init__(
        self,
        *,
        bucket: str,
        region: str,
        prefix: str = "",
        endpoint_url: str = "",
        client: _S3Client | None = None,
    ) -> None:
        self._bucket = bucket.strip()
        self._region = region
        self._prefix = prefix.strip().strip("/")
        self._endpoint_url = endpoint_url.strip()
        self._client = client

    def generate_key(self, *, organization_id: UUID, namespace: str, name: str) -> str:
        return object_key(organization_id=organization_id, namespace=namespace, name=name)

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

    def put(self, key: str, data: bytes, *, content_type: str) -> None:
        try:
            self._require_client().put_object(
                Bucket=self._bucket,
                Key=self._object_key(key),
                Body=data,
                ContentType=content_type or "application/octet-stream",
                ServerSideEncryption="AES256",
            )
        except (NotFoundError, ValidationError):
            raise
        except Exception as exc:
            raise storage_unavailable() from exc

    def get(self, key: str) -> bytes:
        try:
            response = self._require_client().get_object(
                Bucket=self._bucket, Key=self._object_key(key)
            )
            body = response["Body"].read()
            if not isinstance(body, bytes):
                raise storage_unavailable()
            return body
        except (NotFoundError, ValidationError):
            raise
        except Exception as exc:
            if _is_missing_object(exc):
                raise NotFoundError("No se encontró el archivo.") from exc
            raise storage_unavailable() from exc

    def exists(self, key: str) -> bool:
        try:
            self._require_client().head_object(Bucket=self._bucket, Key=self._object_key(key))
            return True
        except Exception as exc:
            if _is_missing_object(exc):
                return False
            raise storage_unavailable() from exc

    def delete(self, key: str) -> None:
        try:
            self._require_client().delete_object(Bucket=self._bucket, Key=self._object_key(key))
        except Exception as exc:
            if _is_missing_object(exc):
                return
            raise storage_unavailable() from exc


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
