from __future__ import annotations

from uuid import UUID

import pytest

from budgetlens.adapters.storage import (
    LocalObjectStorage,
    S3ObjectStorage,
    object_key,
    require_tenant_object_key,
    tenant_prefix,
)
from budgetlens.domain.errors import NotFoundError


class _FakeS3:
    def generate_presigned_url(
        self, ClientMethod: str, Params: dict[str, object], ExpiresIn: int = 900
    ) -> str:
        return (
            f"https://s3.example/{Params['Bucket']}/{Params['Key']}"
            f"?method={ClientMethod}&expires={ExpiresIn}"
        )


ALPHA = UUID(int=1)
BETA = UUID(int=2)
PEPPER = "budgetlens-local-storage-pepper"


def test_object_key_is_prefixed_and_does_not_embed_the_organization_id() -> None:
    key = object_key(organization_id=ALPHA, namespace="imports/a", name="book.csv", pepper=PEPPER)
    assert key.startswith(f"{tenant_prefix(ALPHA, PEPPER)}/")
    assert str(ALPHA) not in key
    require_tenant_object_key(key, ALPHA, PEPPER)
    with pytest.raises(NotFoundError):
        require_tenant_object_key(key, BETA, PEPPER)


def test_local_storage_refuses_to_presign_a_foreign_key(tmp_path) -> None:
    storage = LocalObjectStorage(str(tmp_path), key_pepper=PEPPER)
    key = storage.generate_key(organization_id=ALPHA, namespace="imports/a", name="book.csv")
    assert storage.presign_put(key, organization_id=ALPHA, content_type="text/csv") is None
    with pytest.raises(NotFoundError):
        storage.presign_put(key, organization_id=BETA, content_type="text/csv")


def test_s3_presign_is_issued_only_to_the_owning_tenant() -> None:
    client = _FakeS3()
    storage = S3ObjectStorage(
        bucket="budgetlens-data",
        region="us-east-1",
        prefix="files",
        client=client,  # type: ignore[arg-type]
        key_pepper=PEPPER,
    )
    alpha_key = storage.generate_key(organization_id=ALPHA, namespace="imports/a", name="a.csv")
    signed = storage.presign_put(alpha_key, organization_id=ALPHA, content_type="text/csv")
    assert signed is not None
    assert signed.method == "PUT"
    assert "budgetlens-data" in signed.url
    assert tenant_prefix(ALPHA, PEPPER) in signed.url
    assert str(ALPHA) not in signed.url
    with pytest.raises(NotFoundError):
        storage.presign_put(alpha_key, organization_id=BETA, content_type="text/csv")
    with pytest.raises(NotFoundError):
        storage.presign_get(alpha_key, organization_id=BETA)
