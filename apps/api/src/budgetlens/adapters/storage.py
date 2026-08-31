from __future__ import annotations

from pathlib import Path
from typing import Protocol
from uuid import UUID

from budgetlens.domain.errors import NotFoundError, ValidationError


class ObjectStorage(Protocol):
    def put(self, key: str, data: bytes, *, content_type: str) -> None: ...

    def get(self, key: str) -> bytes: ...

    def exists(self, key: str) -> bool: ...

    def delete(self, key: str) -> None: ...

    def generate_key(self, *, organization_id: UUID, namespace: str, name: str) -> str: ...


class LocalObjectStorage:
    def __init__(self, root: str) -> None:
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def generate_key(self, *, organization_id: UUID, namespace: str, name: str) -> str:
        safe_name = Path(name).name.replace("..", "")
        return f"{organization_id}/{namespace}/{safe_name}"

    def _path(self, key: str) -> Path:
        if key.startswith("/") or ".." in Path(key).parts:
            raise ValidationError("INVALID_OBJECT_KEY", "La clave de almacenamiento no es válida.")
        path = (self._root / key).resolve()
        if not str(path).startswith(str(self._root)):
            raise ValidationError("INVALID_OBJECT_KEY", "La clave de almacenamiento no es válida.")
        return path

    def put(self, key: str, data: bytes, *, content_type: str) -> None:
        del content_type
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes:
        path = self._path(key)
        if not path.is_file():
            raise NotFoundError("No se encontró el archivo.")
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.is_file():
            path.unlink()
