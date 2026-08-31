from __future__ import annotations

import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from budgetlens.config import get_settings

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


class TraceIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        settings = get_settings()
        trace_id = resolve_trace_id(request)
        request.state.trace_id = trace_id
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - started) * 1000)
        response.headers[TRACE_HEADER] = trace_id
        logger.info(
            "http.request.completed",
            extra={
                "event": "http.request.completed",
                "environment": settings.app_env,
                "trace_id": trace_id,
                "duration_ms": duration_ms,
                "outcome": "success" if response.status_code < 500 else "error",
            },
        )
        return response
