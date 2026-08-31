from __future__ import annotations

import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from budgetlens.config import get_settings
from budgetlens.observability import (
    begin_request,
    classify_failure,
    end_request,
    hash_identifier,
    metrics_registry,
    status_class,
)
from budgetlens.runtime import is_shutting_down

TRACE_HEADER = "X-Trace-Id"
SAFE_TRACE_ID = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
TRACEPARENT = re.compile(
    r"^[\da-f]{2}-([\da-f]{32})-[\da-f]{16}-[\da-f]{2}$",
    re.IGNORECASE,
)

logger = logging.getLogger("budgetlens.http")


def parse_traceparent(value: str | None) -> str | None:
    if not value:
        return None
    match = TRACEPARENT.match(value.strip())
    if match is None:
        return None
    return match.group(1).lower()


def resolve_trace_id(request: Request) -> str:
    incoming = request.headers.get(TRACE_HEADER)
    if incoming and SAFE_TRACE_ID.match(incoming.strip()):
        return incoming.strip()
    from_parent = parse_traceparent(request.headers.get("traceparent"))
    if from_parent:
        return from_parent
    return uuid.uuid4().hex


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if isinstance(path, str) and path:
        return path
    return request.url.path


class TraceIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        settings = get_settings()
        if is_shutting_down() and request.method not in {"GET", "HEAD", "OPTIONS"}:
            return JSONResponse(
                status_code=503,
                content={
                    "error": {
                        "code": "SHUTTING_DOWN",
                        "message": "El servicio se está deteniendo. Reintenta en unos segundos.",
                        "field_errors": [],
                        "retryable": True,
                    },
                    "trace_id": "shutdown",
                },
            )
        trace_id = resolve_trace_id(request)
        request_id = uuid.uuid4().hex
        request.state.trace_id = trace_id
        request.state.request_id = request_id
        organization_header = request.headers.get("X-Organization-Id")
        begin_request()
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.error(
                "http.request.failed",
                extra={
                    "event": "http.request.failed",
                    "environment": settings.app_env,
                    "trace_id": trace_id,
                    "request_id": request_id,
                    "organization_id_hash": hash_identifier(organization_header),
                    "user_id_hash": hash_identifier(getattr(request.state, "user_id", None)),
                    "duration_ms": duration_ms,
                    "outcome": "error",
                    "route": _route_template(request),
                    "method": request.method,
                    "status_class": "5xx",
                    "failure_class": classify_failure(status_code=500),
                },
            )
            metrics_registry().record_request(
                method=request.method,
                route=_route_template(request),
                status_code=500,
                duration_ms=duration_ms,
            )
            raise
        finally:
            end_request()
        duration_ms = int((time.perf_counter() - started) * 1000)
        response.headers[TRACE_HEADER] = trace_id
        user_id = getattr(request.state, "user_id", None)
        failure = None
        if response.status_code >= 500:
            failure = classify_failure(status_code=response.status_code)
        elif response.status_code == 503:
            failure = classify_failure(dependency="database")
        logger.info(
            "http.request.completed",
            extra={
                "event": "http.request.completed",
                "environment": settings.app_env,
                "trace_id": trace_id,
                "request_id": request_id,
                "organization_id_hash": hash_identifier(organization_header),
                "user_id_hash": hash_identifier(str(user_id) if user_id else None),
                "duration_ms": duration_ms,
                "outcome": "success" if response.status_code < 500 else "error",
                "route": _route_template(request),
                "method": request.method,
                "status_class": status_class(response.status_code),
                "failure_class": failure,
            },
        )
        metrics_registry().record_request(
            method=request.method,
            route=_route_template(request),
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response
