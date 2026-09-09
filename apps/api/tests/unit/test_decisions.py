from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
DECISIONS = REPO_ROOT / "docs" / "DECISIONS.md"
REQUIRED_FIELDS = (
    "Status",
    "Date",
    "Context",
    "Decision",
    "Positive consequences",
    "Negative consequences",
    "Alternatives",
    "Affected plans / requirements",
)
ALLOWED_STATUSES = frozenset({"proposed", "accepted", "superseded", "rejected"})
EXPECTED_IDS = tuple(f"ADR-{index:03d}" for index in range(1, 14))
HEADING = re.compile(r"^## (ADR-\d{3}) — (.+)$", re.MULTILINE)
FIELD = re.compile(r"^- \*\*(.+?):\*\* (.+)$", re.MULTILINE)


def _parse_adrs() -> dict[str, dict[str, str]]:
    text = DECISIONS.read_text(encoding="utf-8")
    matches = list(HEADING.finditer(text))
    records: dict[str, dict[str, str]] = {}
    for index, match in enumerate(matches):
        adr_id = match.group(1)
        title = match.group(2).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else text.find("\n## Template")
        body = text[start:end] if end != -1 else text[start:]
        fields = {key: value.strip() for key, value in FIELD.findall(body)}
        records[adr_id] = {"title": title, **fields}
    return records


def test_decision_log_lists_required_adrs_with_fields() -> None:
    records = _parse_adrs()
    assert tuple(records) == EXPECTED_IDS
    for adr_id, record in records.items():
        missing = [field for field in REQUIRED_FIELDS if field not in record]
        assert missing == [], f"{adr_id}: {missing}"
        assert record["Status"] in ALLOWED_STATUSES, adr_id
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", record["Date"]), adr_id
        assert record["Decision"]
        assert record["Alternatives"]


def test_proposed_conversation_policy_is_not_accepted() -> None:
    record = _parse_adrs()["ADR-012"]
    assert record["Status"] == "proposed"
    assert "pending" in record["Decision"].lower()


def test_accepted_adrs_are_not_rewritten_as_tables_only() -> None:
    text = DECISIONS.read_text(encoding="utf-8")
    assert "Do not rewrite an accepted entry" in text
    assert "proposed" in text
    for adr_id in EXPECTED_IDS:
        assert f"## {adr_id} — " in text
