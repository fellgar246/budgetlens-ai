from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from budgetlens.domain.enums import ScenarioType


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def import_idempotency_fingerprint(
    *,
    file_sha256: str,
    mapping: dict[str, Any],
    organization_id: UUID,
    scenario_type: ScenarioType,
    budget_version_id: UUID | None,
) -> str:
    payload = canonical_json(
        {
            "file_sha256": file_sha256.lower(),
            "mapping": mapping,
            "organization_id": str(organization_id),
            "scenario_type": scenario_type.value,
            "budget_version_id": str(budget_version_id) if budget_version_id else None,
        }
    )
    return sha256_hex(payload.encode("utf-8"))
