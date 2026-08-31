from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime
from uuid import UUID

from budgetlens.domain.enums import ExportJobStatus, ExportType
from budgetlens.domain.errors import NotFoundError
from budgetlens.domain.text_safety import neutralize_csv_text


@dataclass(frozen=True, slots=True)
class ExportJob:
    id: UUID
    organization_id: UUID
    created_by: UUID
    export_type: ExportType
    format: str
    filters_json: dict[str, object]
    object_key: str
    filename: str
    status: ExportJobStatus
    created_at: datetime
    expires_at: datetime

    def is_expired(self, *, now: datetime) -> bool:
        return now >= self.expires_at or self.status is ExportJobStatus.EXPIRED

    def mark_expired(self) -> ExportJob:
        return replace(self, status=ExportJobStatus.EXPIRED)

    def assert_downloadable(self, *, now: datetime) -> None:
        if self.is_expired(now=now):
            raise NotFoundError()


def export_filename(*, period_from: date, period_to: date) -> str:
    start = period_from.strftime("%Y-%m")
    end = period_to.strftime("%Y-%m")
    return f"budgetlens-variance-{start}_{end}.csv"


def render_csv(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    *,
    with_bom: bool = True,
) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow([neutralize_csv_text(cell) for cell in row])
    text = buffer.getvalue()
    if with_bom:
        text = f"\ufeff{text}"
    return text.encode("utf-8")
