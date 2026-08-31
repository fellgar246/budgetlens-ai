from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from budgetlens.domain.errors import DomainError
from budgetlens.presentation.middleware import TRACE_HEADER

logger = logging.getLogger("budgetlens.errors")


def _trace_id(request: Request) -> str:
    return str(getattr(request.state, "trace_id", "unknown"))


def error_body(
    *,
    code: str,
    message: str,
    trace_id: str,
    retryable: bool,
    field_errors: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "field_errors": field_errors or [],
            "retryable": retryable,
        },
        "trace_id": trace_id,
    }


async def validation_handler(request: Request, _exc: Exception) -> JSONResponse:
    trace_id = _trace_id(request)
    return JSONResponse(
        status_code=400,
        content=error_body(
            code="INVALID_REQUEST",
            message="La solicitud no tiene el formato esperado.",
            trace_id=trace_id,
            retryable=False,
        ),
        headers={TRACE_HEADER: trace_id},
    )


async def domain_handler(request: Request, exc: Exception) -> JSONResponse:
    trace_id = _trace_id(request)
    error = (
        exc
        if isinstance(exc, DomainError)
        else DomainError(
            code="INTERNAL_ERROR",
            message="Ocurrió un error interno.",
            status_code=500,
            retryable=True,
        )
    )
    return JSONResponse(
        status_code=error.status_code,
        content=error_body(
            code=error.code,
            message=error.message,
            trace_id=trace_id,
            retryable=error.retryable,
            field_errors=error.field_errors,
        ),
        headers={TRACE_HEADER: trace_id},
    )


async def http_handler(request: Request, exc: Exception) -> JSONResponse:
    trace_id = _trace_id(request)
    status_code = exc.status_code if isinstance(exc, StarletteHTTPException) else 500
    if status_code == 401:
        message = "Debes iniciar sesión para continuar."
        code = "UNAUTHENTICATED"
    elif status_code == 403:
        message = "No tienes permiso para esta acción."
        code = "FORBIDDEN"
    elif status_code == 404:
        message = "No se encontró el recurso."
        code = "NOT_FOUND"
    else:
        message = "La solicitud no se pudo completar."
        code = "HTTP_ERROR"
    return JSONResponse(
        status_code=status_code,
        content=error_body(
            code=code,
            message=message,
            trace_id=trace_id,
            retryable=False,
        ),
        headers={TRACE_HEADER: trace_id},
    )


async def unhandled_handler(request: Request, _exc: Exception) -> JSONResponse:
    trace_id = _trace_id(request)
    logger.error(
        "http.unhandled_error",
        extra={"event": "http.unhandled_error", "trace_id": trace_id, "outcome": "error"},
    )
    return JSONResponse(
        status_code=500,
        content=error_body(
            code="INTERNAL_ERROR",
            message=(
                "Ocurrió un error interno. "
                "Usa el identificador de seguimiento si necesitas soporte."
            ),
            trace_id=trace_id,
            retryable=True,
        ),
        headers={TRACE_HEADER: trace_id},
    )


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, domain_handler)
    app.add_exception_handler(RequestValidationError, validation_handler)
    app.add_exception_handler(StarletteHTTPException, http_handler)
    app.add_exception_handler(Exception, unhandled_handler)
