from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from budgetlens.adapters.ai import BedrockAIProvider, DeterministicAIProvider
from budgetlens.adapters.exports import InlineExportExecutor, ProcessExportExecutor
from budgetlens.adapters.factory import (
    build_ai_provider,
    build_export_runner,
    build_import_runner,
    build_object_storage,
)
from budgetlens.adapters.identity import DevIdentityAdapter, OidcIdentityAdapter
from budgetlens.adapters.imports import InlineImportExecutor, ProcessImportExecutor
from budgetlens.adapters.storage import LocalObjectStorage, S3ObjectStorage
from budgetlens.config import Settings
from budgetlens.domain.errors import (
    DependencyUnavailableError,
    NotFoundError,
    UnauthenticatedError,
)
from budgetlens.domain.organization import User
from budgetlens.ports.ai import ProviderResult


class _FakeBody:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_object(self, **kwargs: object) -> None:
        key = str(kwargs["Key"])
        body = kwargs["Body"]
        assert isinstance(body, bytes)
        self.objects[key] = body

    def get_object(self, **kwargs: object) -> dict[str, _FakeBody]:
        key = str(kwargs["Key"])
        if key not in self.objects:
            raise _MissingKey()
        return {"Body": _FakeBody(self.objects[key])}

    def head_object(self, **kwargs: object) -> None:
        if str(kwargs["Key"]) not in self.objects:
            raise _MissingKey()

    def delete_object(self, **kwargs: object) -> None:
        self.objects.pop(str(kwargs["Key"]), None)


class _MissingKey(Exception):
    response = {"Error": {"Code": "NoSuchKey"}}


class _UserLookup:
    def __init__(self, user: User | None) -> None:
        self._user = user

    def get(self, user_id: UUID) -> User | None:
        if self._user is None or self._user.id != user_id:
            return None
        return self._user


def _settings(**overrides: object) -> Settings:
    payload: dict[str, object] = {
        "app_env": "test",
        "database_url": "postgresql+psycopg://budgetlens:x@localhost:5432/budgetlens",
    }
    payload.update(overrides)
    return Settings.model_validate(payload)


def test_factory_selects_local_storage_and_stub_ai() -> None:
    settings = _settings()
    assert isinstance(build_object_storage(settings), LocalObjectStorage)
    assert isinstance(build_ai_provider(settings), DeterministicAIProvider)
    assert isinstance(build_import_runner(settings), InlineImportExecutor)
    assert isinstance(build_export_runner(settings), InlineExportExecutor)


def test_factory_selects_s3_bedrock_and_process_executor() -> None:
    settings = _settings(
        object_storage_backend="s3",
        s3_bucket="budgetlens-data",
        ai_provider="bedrock",
        bedrock_model_id="model",
        import_executor="process",
        export_executor="process",
    )
    assert isinstance(build_object_storage(settings), S3ObjectStorage)
    assert isinstance(build_ai_provider(settings), BedrockAIProvider)
    assert isinstance(build_import_runner(settings), ProcessImportExecutor)
    assert isinstance(build_export_runner(settings), ProcessExportExecutor)


def test_s3_adapter_round_trip_and_missing_object() -> None:
    client = FakeS3Client()
    storage = S3ObjectStorage(
        bucket="budgetlens-data", region="us-east-1", prefix="files", client=client
    )
    key = storage.generate_key(organization_id=UUID(int=1), namespace="imports/a", name="book.csv")
    assert str(UUID(int=1)) not in key
    assert "book.csv" in key
    storage.put(key, b"period,amount", content_type="text/csv")
    assert storage.exists(key) is True
    assert storage.get(key) == b"period,amount"
    storage.delete(key)
    assert storage.exists(key) is False
    with pytest.raises(NotFoundError):
        storage.get(key)


def test_s3_adapter_without_client_or_sdk_is_unavailable() -> None:
    storage = S3ObjectStorage(bucket="budgetlens-data", region="us-east-1")
    with pytest.raises(DependencyUnavailableError) as exc:
        storage.put("org/imports/a.csv", b"x", content_type="text/csv")
    assert exc.value.code == "STORAGE_UNAVAILABLE"
    assert exc.value.retryable is True
    assert "archivo" in exc.value.message


def test_bedrock_parses_tool_use_and_maps_failures() -> None:
    class FakeBedrock:
        def converse(self, **kwargs: object) -> dict[str, object]:
            del kwargs
            return {
                "output": {
                    "message": {
                        "content": [
                            {"toolUse": {"name": "get_variance_summary", "input": {}}},
                        ]
                    }
                },
                "usage": {"inputTokens": 3, "outputTokens": 2},
            }

    provider = BedrockAIProvider(
        region="us-east-1", model_id="model", timeout_seconds=20, client=FakeBedrock()
    )
    result = provider.complete(messages=[], question="resumen", settings=_settings())
    assert isinstance(result, ProviderResult)
    assert result.tool_requests[0].name == "get_variance_summary"
    assert result.model_id == "model"

    class BrokenBedrock:
        def converse(self, **kwargs: object) -> dict[str, object]:
            del kwargs
            raise RuntimeError("timeout")

    broken = BedrockAIProvider(
        region="us-east-1", model_id="model", timeout_seconds=20, client=BrokenBedrock()
    )
    with pytest.raises(DependencyUnavailableError) as exc:
        broken.complete(messages=[], question="resumen", settings=_settings())
    assert exc.value.code == "AI_UNAVAILABLE"
    assert exc.value.retryable is True


def test_dev_identity_accepts_uuid_and_oidc_fails_closed() -> None:
    from budgetlens.domain.enums import UserStatus

    now = datetime(2026, 1, 1, tzinfo=UTC)
    user = User(
        id=UUID(int=11),
        email="ana@example.com",
        display_name="Ana",
        status=UserStatus.ACTIVE,
        external_subject=None,
        created_at=now,
        updated_at=now,
        platform_role=None,
    )
    adapter = DevIdentityAdapter(_UserLookup(user))  # type: ignore[arg-type]
    assert adapter.authenticate(str(user.id)).email == "ana@example.com"
    with pytest.raises(UnauthenticatedError):
        adapter.authenticate("not-a-uuid")
    with pytest.raises(UnauthenticatedError):
        OidcIdentityAdapter().authenticate("any-token")


def test_import_executor_runs_work() -> None:
    seen: list[str] = []

    def work() -> str:
        seen.append("ran")
        return "ok"

    assert InlineImportExecutor().run("validate", work) == "ok"
    assert ProcessImportExecutor().run("apply", work) == "ok"
    assert seen == ["ran", "ran"]


def test_export_executor_runs_work() -> None:
    seen: list[str] = []

    def work() -> str:
        seen.append("ran")
        return "ready"

    assert InlineExportExecutor().run("export", work) == "ready"
    assert ProcessExportExecutor().run("export", work) == "ready"
    assert seen == ["ran", "ran"]


def test_ready_503_has_no_internal_details(monkeypatch: pytest.MonkeyPatch) -> None:
    from budgetlens.adapters.db import reset_engine
    from budgetlens.config import reset_settings_cache
    from budgetlens.presentation.app import create_app

    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://budgetlens:x@127.0.0.1:1/budgetlens",
    )
    reset_settings_cache()
    reset_engine()
    client = TestClient(create_app())
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable"
    assert "password" not in str(body).lower()
    assert "traceback" not in str(body).lower()


def test_database_error_on_request_is_503(monkeypatch: pytest.MonkeyPatch) -> None:
    from sqlalchemy.exc import OperationalError

    from budgetlens.adapters.db import reset_engine
    from budgetlens.config import reset_settings_cache
    from budgetlens.presentation.app import create_app

    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://budgetlens:budgetlens_local_only@127.0.0.1:5433/budgetlens",
    )
    reset_settings_cache()
    reset_engine()

    def boom() -> object:
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    monkeypatch.setattr("budgetlens.presentation.deps.get_session_factory", boom)
    client = TestClient(create_app())
    response = client.get(
        "/api/v1/me",
        headers={"Authorization": "Bearer 11111111-1111-4111-8111-111111111111"},
    )
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert body["error"]["retryable"] is True
    assert "connection refused" not in str(body).lower()
    assert "SELECT" not in str(body)
