from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from budgetlens.adapters.persistence.models import IdempotencyRecordRow
from budgetlens.adapters.persistence.repositories import SqlIdempotencyRepository
from budgetlens.domain.errors import ConflictError, ValidationError, field_issue
from budgetlens.domain.idempotency import sha256_hex
from budgetlens.domain.identities import Clock, IdFactory


def require_idempotency_key(value: str | None) -> str:
    cleaned = (value or "").strip()
    if not cleaned or len(cleaned) > 128:
        raise ValidationError(
            "IDEMPOTENCY_KEY_REQUIRED",
            "Esta acción requiere una clave de idempotencia.",
            field_errors=[
                field_issue(
                    "Idempotency-Key",
                    "IDEMPOTENCY_KEY_REQUIRED",
                    "Esta acción requiere una clave de idempotencia.",
                )
            ],
        )
    return cleaned


def replay_or_reserve(
    session: Session,
    *,
    organization_id: UUID,
    user_id: UUID,
    operation: str,
    idempotency_key: str,
    resource_id: UUID,
    request_hash: str,
    clock: Clock,
    ids: IdFactory,
) -> UUID | None:
    key = require_idempotency_key(idempotency_key)
    store = SqlIdempotencyRepository(session, organization_id)
    existing = store.get(user_id=user_id, operation=operation, key=key)
    if existing is not None:
        if existing.request_hash != request_hash:
            raise ConflictError(
                "IDEMPOTENCY_CONFLICT",
                "La clave de idempotencia ya se usó con otra solicitud.",
            )
        return existing.resource_id
    store.add(
        IdempotencyRecordRow(
            id=ids.new_id(),
            organization_id=organization_id,
            user_id=user_id,
            operation=operation,
            key=key,
            request_hash=request_hash,
            resource_id=resource_id,
            created_at=clock.now(),
        )
    )
    return None


def hash_payload(*parts: str) -> str:
    return sha256_hex("|".join(parts).encode())
