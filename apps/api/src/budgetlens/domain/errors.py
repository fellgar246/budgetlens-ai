from __future__ import annotations

from dataclasses import dataclass, field


def field_issue(field: str, code: str, message: str) -> dict[str, str]:
    return {"field": field, "code": code, "message": message}


def _empty_field_errors() -> list[dict[str, str]]:
    return []


@dataclass(eq=False)
class DomainError(Exception):
    code: str
    message: str
    status_code: int
    field_errors: list[dict[str, str]] = field(default_factory=_empty_field_errors)
    retryable: bool = False

    def __str__(self) -> str:
        return self.message


class ValidationError(DomainError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        field_errors: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=422,
            field_errors=field_errors or [],
        )


class ConflictError(DomainError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        field_errors: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=409,
            field_errors=field_errors or [],
        )


class ConcurrencyError(ConflictError):
    def __init__(self) -> None:
        super().__init__(
            "CONCURRENCY_CONFLICT",
            "Otro cambio se aplicó primero. Recarga e inténtalo de nuevo.",
        )


class NotFoundError(DomainError):
    def __init__(self, message: str = "No se encontró el recurso.") -> None:
        super().__init__(code="NOT_FOUND", message=message, status_code=404)


class PermissionDeniedError(DomainError):
    def __init__(self, message: str = "No tienes permiso para esta acción.") -> None:
        super().__init__(code="FORBIDDEN", message=message, status_code=403)


class UnauthenticatedError(DomainError):
    def __init__(self, message: str = "Debes iniciar sesión para continuar.") -> None:
        super().__init__(code="UNAUTHENTICATED", message=message, status_code=401)


class PayloadTooLargeError(DomainError):
    def __init__(self, message: str = "El archivo excede el tamaño permitido.") -> None:
        super().__init__(code="FILE_TOO_LARGE", message=message, status_code=413)


class RateLimitError(DomainError):
    def __init__(
        self, message: str = "Demasiadas solicitudes. Espera un momento e inténtalo de nuevo."
    ) -> None:
        super().__init__(code="RATE_LIMITED", message=message, status_code=429, retryable=True)


class DependencyUnavailableError(DomainError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code=code, message=message, status_code=503, retryable=True)


def storage_unavailable() -> DependencyUnavailableError:
    return DependencyUnavailableError(
        "STORAGE_UNAVAILABLE",
        "No se pudo guardar o leer el archivo. Inténtalo de nuevo.",
    )


def ai_unavailable() -> DependencyUnavailableError:
    return DependencyUnavailableError(
        "AI_UNAVAILABLE",
        "El copiloto no está disponible. Inténtalo de nuevo.",
    )


def database_unavailable() -> DependencyUnavailableError:
    return DependencyUnavailableError(
        "DATABASE_UNAVAILABLE",
        "El servicio no está disponible. Inténtalo de nuevo.",
    )


class CircuitOpenError(DependencyUnavailableError):
    def __init__(self, dependency: str) -> None:
        if dependency == "ai":
            super().__init__(
                "AI_UNAVAILABLE",
                "El copiloto no está disponible. Inténtalo de nuevo.",
            )
        else:
            super().__init__(
                "STORAGE_UNAVAILABLE",
                "No se pudo guardar o leer el archivo. Inténtalo de nuevo.",
            )
        self.dependency = dependency
