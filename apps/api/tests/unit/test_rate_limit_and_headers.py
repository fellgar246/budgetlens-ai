from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from budgetlens.application.rate_limit import enforce_limit, limiter
from budgetlens.domain.errors import RateLimitError
from budgetlens.observability import classify_failure, metrics_registry


def test_rate_limiter_blocks_after_limit() -> None:
    limiter().reset()
    user = UUID(int=9)
    enforce_limit("upload", user, limit=2, window_seconds=60)
    enforce_limit("upload", user, limit=2, window_seconds=60)
    with pytest.raises(RateLimitError) as exc:
        enforce_limit("upload", user, limit=2, window_seconds=60)
    assert exc.value.status_code == 429
    assert exc.value.retryable is True


def test_security_headers_are_present(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_metrics_record_request_without_tenant_labels(client: TestClient) -> None:
    client.get("/api/v1/health/live")
    snapshot = metrics_registry().snapshot()
    assert snapshot["active_requests"] == 0
    assert all("organization" not in str(item).lower() for item in snapshot["requests"])
    assert snapshot["ai"]["estimated_cost"] is None


def test_failure_classes_are_distinct() -> None:
    assert classify_failure(dependency="database") == "dependency"
    assert classify_failure(status_code=500) == "application"
    assert classify_failure(status_code=503, dependency="storage") == "dependency"
    assert classify_failure() == "infrastructure"


def test_export_job_rejects_expired_download() -> None:
    from datetime import UTC, datetime, timedelta
    from uuid import UUID

    from budgetlens.domain.enums import ExportJobStatus, ExportType
    from budgetlens.domain.errors import NotFoundError
    from budgetlens.domain.exporting import ExportJob

    now = datetime(2026, 8, 31, tzinfo=UTC)
    job = ExportJob(
        id=UUID(int=1),
        organization_id=UUID(int=2),
        created_by=UUID(int=3),
        export_type=ExportType.VARIANCE_BREAKDOWN,
        format="csv",
        filters_json={},
        object_key="exports/a.csv",
        filename="a.csv",
        status=ExportJobStatus.READY,
        created_at=now - timedelta(hours=25),
        expires_at=now - timedelta(minutes=1),
    )
    with pytest.raises(NotFoundError):
        job.assert_downloadable(now=now)
