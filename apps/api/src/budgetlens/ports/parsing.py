from __future__ import annotations

from typing import Protocol

from budgetlens.domain.importing import WorkbookTable


class WorkbookParser(Protocol):
    def parse(
        self,
        filename: str,
        content: bytes,
        *,
        media_type: str | None = None,
        sheet_name: str | None = None,
        delimiter: str | None = None,
    ) -> WorkbookTable: ...
