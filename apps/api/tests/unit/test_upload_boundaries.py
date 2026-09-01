from __future__ import annotations

import io
import zipfile

import pytest

from budgetlens.adapters.parsing import parse_workbook
from budgetlens.domain.errors import PayloadTooLargeError, ValidationError


def test_overlong_csv_cell_is_rejected() -> None:
    content = ("period,amount\n2026-01," + ("9" * 501)).encode("utf-8")
    with pytest.raises(ValidationError) as exc:
        parse_workbook("book.csv", content, media_type="text/csv")
    assert exc.value.code == "UNSUPPORTED_FILE"


def test_disproportionate_xlsx_zip_is_rejected() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("xl/workbook.xml", b"\x00" * 2_000_000)
    with pytest.raises(PayloadTooLargeError):
        parse_workbook("book.xlsx", buffer.getvalue())


def test_tool_schemas_are_closed() -> None:
    from budgetlens.adapters.ai import TOOL_SPECS

    for spec in TOOL_SPECS:
        schema = spec["toolSpec"]["inputSchema"]["json"]
        assert schema["additionalProperties"] is False
