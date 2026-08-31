from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from budgetlens.config import Settings, get_settings
from budgetlens.logging import configure_logging
from budgetlens.presentation.errors import install_error_handlers
from budgetlens.presentation.middleware import TraceIdMiddleware
from budgetlens.presentation.routes.analytics import router as analytics_router
from budgetlens.presentation.routes.audit import router as audit_router
from budgetlens.presentation.routes.budget_versions import router as budget_versions_router
from budgetlens.presentation.routes.conversations import router as conversations_router
from budgetlens.presentation.routes.dev import router as dev_router
from budgetlens.presentation.routes.dimensions import router as dimensions_router
from budgetlens.presentation.routes.health import router as health_router
from budgetlens.presentation.routes.imports import router as imports_router
from budgetlens.presentation.routes.memberships import router as memberships_router
from budgetlens.presentation.routes.ops import router as ops_router
from budgetlens.presentation.routes.scenarios import router as scenarios_router
from budgetlens.presentation.routes.session import router as session_router
from budgetlens.presentation.security_headers import SecurityHeadersMiddleware
from budgetlens.runtime import mark_shutting_down, reset_runtime


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    reset_runtime()
    try:
        yield
    finally:
        mark_shutting_down()


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    configure_logging(resolved)
    docs_url = "/docs" if resolved.docs_enabled else None
    app = FastAPI(
        title="BudgetLens API",
        version=resolved.app_version,
        docs_url=docs_url,
        redoc_url="/redoc" if docs_url else None,
        openapi_url="/openapi.json" if docs_url else None,
        lifespan=_lifespan,
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(TraceIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Organization-Id",
            "X-Trace-Id",
            "Idempotency-Key",
            "traceparent",
        ],
        expose_headers=["X-Trace-Id"],
    )
    install_error_handlers(app)
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(session_router, prefix="/api/v1")
    app.include_router(memberships_router, prefix="/api/v1")
    app.include_router(dimensions_router, prefix="/api/v1")
    app.include_router(budget_versions_router, prefix="/api/v1")
    app.include_router(imports_router, prefix="/api/v1")
    app.include_router(analytics_router, prefix="/api/v1")
    app.include_router(scenarios_router, prefix="/api/v1")
    app.include_router(conversations_router, prefix="/api/v1")
    app.include_router(audit_router, prefix="/api/v1")
    app.include_router(ops_router, prefix="/api/v1")
    if resolved.auth_mode == "dev" and resolved.app_env in {"local", "test"}:
        app.include_router(dev_router, prefix="/api/v1")
    return app
