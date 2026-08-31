from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from budgetlens.config import Settings, get_settings
from budgetlens.logging import configure_logging
from budgetlens.presentation.errors import install_error_handlers
from budgetlens.presentation.middleware import TraceIdMiddleware
from budgetlens.presentation.routes.health import router as health_router


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
    )
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
            "traceparent",
        ],
        expose_headers=["X-Trace-Id"],
    )
    install_error_handlers(app)
    app.include_router(health_router, prefix="/api/v1")
    return app
