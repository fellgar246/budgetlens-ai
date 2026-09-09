from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
API_DOCKERFILE = (REPO_ROOT / "apps" / "api" / "Dockerfile").read_text(encoding="utf-8")
WEB_DOCKERFILE = (REPO_ROOT / "apps" / "web" / "Dockerfile").read_text(encoding="utf-8")
RELEASE_COMPOSE = (REPO_ROOT / "compose.release.yaml").read_text(encoding="utf-8")
SCAN = (REPO_ROOT / "scripts" / "scan.sh").read_text(encoding="utf-8")


def test_api_image_is_multistage_non_root_and_has_healthcheck() -> None:
    assert "FROM python:3.12.11-slim-bookworm AS builder" in API_DOCKERFILE
    assert "FROM python:3.12.11-slim-bookworm" in API_DOCKERFILE
    assert "USER 10001" in API_DOCKERFILE
    assert "HEALTHCHECK" in API_DOCKERFILE
    assert "/api/v1/health/live" in API_DOCKERFILE
    assert "uv sync --frozen --no-dev --no-editable" in API_DOCKERFILE


def test_web_release_image_is_non_root_with_healthcheck() -> None:
    assert "FROM nginx:1.27-alpine AS release" in WEB_DOCKERFILE
    assert "USER nginx" in WEB_DOCKERFILE
    assert "HEALTHCHECK" in WEB_DOCKERFILE
    assert "nginx.main.conf" in WEB_DOCKERFILE
    assert (REPO_ROOT / "apps" / "web" / "nginx.main.conf").is_file()
    main = (REPO_ROOT / "apps" / "web" / "nginx.main.conf").read_text(encoding="utf-8")
    assert "pid /tmp/nginx.pid" in main


def test_release_compose_uses_read_only_root_and_explicit_write_paths() -> None:
    assert "read_only: true" in RELEASE_COMPOSE
    assert "/tmp" in RELEASE_COMPOSE
    assert "./var/storage:/var/lib/budgetlens/storage" in RELEASE_COMPOSE
    assert 'user: "10001:10001"' in RELEASE_COMPOSE
    assert "target: release" in RELEASE_COMPOSE
    assert 'API_RELOAD: "0"' in RELEASE_COMPOSE


def test_scan_covers_sbom_deps_secrets_and_images() -> None:
    assert "sbom" in SCAN
    assert "pip-audit" in SCAN
    assert "pnpm audit" in SCAN
    assert "AKIA" in SCAN
    assert "trivy image" in SCAN
    assert "checkov" in SCAN
    assert "var/sbom" in SCAN
