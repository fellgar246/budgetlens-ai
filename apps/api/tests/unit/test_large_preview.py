from __future__ import annotations

import time

import pytest

from budgetlens.adapters.parsing import parse_workbook


@pytest.mark.perf
def test_large_csv_preview_completes_under_a_minute() -> None:
    header = "period,account_code,department_code,amount,currency,note\n"
    row = "2026-01,6100,OPS,100.0000,MXN," + ("x" * 400) + "\n"
    target_bytes = 25 * 1024 * 1024
    chunks = [header]
    size = len(header.encode("utf-8"))
    row_bytes = len(row.encode("utf-8"))
    while size < target_bytes:
        chunks.append(row)
        size += row_bytes
    content = "".join(chunks).encode("utf-8")
    repeats = len(chunks) - 1
    assert repeats < 100_000
    assert len(content) >= target_bytes
    started = time.perf_counter()
    table = parse_workbook("large-preview.csv", content, media_type="text/csv")
    elapsed = time.perf_counter() - started
    assert table.headers[0] == "period"
    assert len(table.rows) == repeats
    assert elapsed < 60
