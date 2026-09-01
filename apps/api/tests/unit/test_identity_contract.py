from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from budgetlens.domain.enums import OrganizationStatus
from budgetlens.domain.identities import format_rfc3339
from budgetlens.domain.money import Currency
from budgetlens.domain.organization import Organization
from budgetlens.presentation.schemas import organization_response


def test_api_payloads_use_uuid_strings_and_rfc3339() -> None:
    now = datetime(2026, 1, 15, 8, 30, tzinfo=UTC)
    organization = Organization(
        id=UUID("11111111-1111-4111-8111-111111111111"),
        name="Alpha",
        slug="alpha",
        functional_currency=Currency("MXN"),
        fiscal_year_start_month=1,
        status=OrganizationStatus.ACTIVE,
        created_at=now,
        updated_at=now,
        version=1,
    )
    payload = organization_response(organization).model_dump(mode="json")
    assert payload["id"] == "11111111-1111-4111-8111-111111111111"
    assert isinstance(payload["id"], str)
    created_at = payload["created_at"]
    assert created_at in {format_rfc3339(now), "2026-01-15T08:30:00+00:00"}
    UUID(payload["id"])
