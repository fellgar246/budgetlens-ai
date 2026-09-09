from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PresignedObject:
    method: str
    url: str
    expires_in: int


class ObjectStorage(Protocol):
    def put(self, key: str, data: bytes, *, content_type: str) -> None: ...

    def get(self, key: str) -> bytes: ...

    def exists(self, key: str) -> bool: ...

    def delete(self, key: str) -> None: ...

    def generate_key(self, *, organization_id: UUID, namespace: str, name: str) -> str: ...

    def assert_tenant_key(self, key: str, *, organization_id: UUID) -> None: ...

    def presign_put(
        self,
        key: str,
        *,
        organization_id: UUID,
        content_type: str,
        expires_in: int = 900,
    ) -> PresignedObject | None: ...

    def presign_get(
        self,
        key: str,
        *,
        organization_id: UUID,
        expires_in: int = 900,
    ) -> PresignedObject | None: ...
