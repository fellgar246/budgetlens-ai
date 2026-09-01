#!/usr/bin/env python3
"""Regenerate versioned XLSX import fixtures under sample-data/."""

from __future__ import annotations

import csv
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "sample-data"


def _csv_to_xlsx(source: Path, target: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    with source.open(encoding="utf-8") as handle:
        for row in csv.reader(handle):
            sheet.append(row)
    workbook.save(target)


def _formula_xlsx(target: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.append(
        ["period", "account_code", "department_code", "cost_center_code", "amount", "currency"]
    )
    sheet.append(["2026-01", "6100", "OPS", "CC-GEN", "=1+1", "MXN"])
    workbook.save(target)


def main() -> None:
    SAMPLE.mkdir(parents=True, exist_ok=True)
    _csv_to_xlsx(SAMPLE / "budget-valid.csv", SAMPLE / "budget-valid.xlsx")
    _formula_xlsx(SAMPLE / "formula.xlsx")
    print(SAMPLE / "budget-valid.xlsx")
    print(SAMPLE / "formula.xlsx")


if __name__ == "__main__":
    main()
