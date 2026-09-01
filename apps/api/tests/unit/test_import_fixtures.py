from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SAMPLE = ROOT / "sample-data"
REQUIRED = (
    "budget-valid.csv",
    "actuals-valid.csv",
    "budget-valid.xlsx",
    "leading-zero.csv",
    "locale-ambiguous.csv",
    "formula.xlsx",
    "unknown-dimension.csv",
    "duplicates.csv",
)


def test_sample_data_includes_required_import_fixtures() -> None:
    missing = [name for name in REQUIRED if not (SAMPLE / name).is_file()]
    assert missing == []
    budget = (SAMPLE / "budget-valid.csv").read_text(encoding="utf-8")
    actuals = (SAMPLE / "actuals-valid.csv").read_text(encoding="utf-8")
    assert "0.0000" in budget
    assert any(",0.0000,MXN" in line for line in actuals.splitlines())
