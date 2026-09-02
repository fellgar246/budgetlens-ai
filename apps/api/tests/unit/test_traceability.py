from __future__ import annotations

from collections.abc import Iterable, Mapping

from tests.traceability_catalog import (
    ACCEPTANCE_CRITERIA,
    AGENT_ACCEPTANCE_VALUES,
    BACKLOG,
    DOC_PATHS,
    FUNCTIONAL_GROUPS,
    FUNCTIONAL_REQUIREMENTS,
    GATES,
    NON_FUNCTIONAL_REQUIREMENTS,
    PLANS,
    PROTECTED_ACCEPTANCE_CATEGORIES,
    REPO_ROOT,
    RISKS,
    acceptance_by_id,
    deferred_requirements,
    evidence_exists,
    expected_acceptance_ids,
    expected_functional_ids,
    expected_gate_ids,
    expected_nfr_ids,
    expected_plan_ids,
    expected_risk_ids,
    gate_release_blockers,
    requirement_by_id,
    risk_release_blockers,
)


def _ids(rows: Iterable[Mapping[str, object]], key: str = "id") -> list[str]:
    return [str(row[key]) for row in rows]


def _docs_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in DOC_PATHS)


def test_every_functional_requirement_appears_in_a_matrix_row() -> None:
    expected = expected_functional_ids()
    listed = _ids(FUNCTIONAL_REQUIREMENTS)
    grouped = [item_id for group in FUNCTIONAL_GROUPS for item_id in group["ids"]]
    assert listed == expected
    assert grouped == expected


def test_every_nfr_appears_in_the_matrix() -> None:
    assert _ids(NON_FUNCTIONAL_REQUIREMENTS) == expected_nfr_ids()


def test_every_plan_declares_requirements_and_acceptance() -> None:
    assert _ids(PLANS) == expected_plan_ids()
    for plan in PLANS:
        assert plan["requirements"], plan["id"]
        assert plan["acceptance"], plan["id"]
        for requirement_id in plan["requirements"]:
            requirement_by_id(requirement_id)
        for acceptance_id in plan["acceptance"]:
            acceptance_by_id(acceptance_id)


def test_every_requirement_is_owned_by_a_plan() -> None:
    owned = {requirement_id for plan in PLANS for requirement_id in plan["requirements"]}
    missing = [
        item["id"]
        for item in [*FUNCTIONAL_REQUIREMENTS, *NON_FUNCTIONAL_REQUIREMENTS]
        if item["id"] not in owned
    ]
    assert missing == []


def test_every_acceptance_criterion_has_a_suite_or_runbook() -> None:
    assert _ids(ACCEPTANCE_CRITERIA) == expected_acceptance_ids()
    for item in ACCEPTANCE_CRITERIA:
        assert item["kind"] in {"suite", "runbook", "both"}
        assert item["evidence"], item["id"]
        missing = [reference for reference in item["evidence"] if not evidence_exists(reference)]
        assert missing == [], f"{item['id']}: {missing}"


def test_implemented_requirements_have_existing_evidence() -> None:
    for item in [*FUNCTIONAL_REQUIREMENTS, *NON_FUNCTIONAL_REQUIREMENTS]:
        if item["status"] == "deferred":
            continue
        references = list(item["evidence"])
        if "acceptance" in item:
            for acceptance_id in item["acceptance"]:
                references.extend(acceptance_by_id(acceptance_id)["evidence"])
        assert references, item["id"]
        missing = [reference for reference in references if not evidence_exists(reference)]
        assert missing == [], f"{item['id']}: {missing}"


def test_every_gate_has_owner_and_moment() -> None:
    assert _ids(GATES) == expected_gate_ids()
    for gate in GATES:
        assert gate["owner"].strip(), gate["id"]
        assert gate["moment"].strip(), gate["id"]
        assert gate["plans"], gate["id"]
        assert gate["local_simulation"].strip(), gate["id"]
        assert gate["blocks"].strip(), gate["id"]
        assert gate["deliverables"], gate["id"]
        assert gate["human_actions"], gate["id"]


def test_high_impact_risks_have_mitigation_and_signal() -> None:
    assert _ids(RISKS) == expected_risk_ids()
    for risk in RISKS:
        if risk["impact"] != "high":
            continue
        assert risk["mitigation"].strip(), risk["id"]
        assert risk["trigger"].strip(), risk["id"]
        assert risk["evidence"], risk["id"]
        missing = [reference for reference in risk["evidence"] if not evidence_exists(reference)]
        assert missing == [], f"{risk['id']}: {missing}"


def test_high_impact_unverified_risks_block_named_releases() -> None:
    assert risk_release_blockers("local") == []
    assert risk_release_blockers("aws") == ["R-06", "R-15"]
    assert risk_release_blockers("prod") == ["R-06", "R-15"]
    assert "M-01" in gate_release_blockers("aws")
    assert "M-10" in gate_release_blockers("prod")
    assert gate_release_blockers("local") == []


def test_must_requirements_are_not_deferred() -> None:
    deferred_must = [
        item["id"]
        for item in FUNCTIONAL_REQUIREMENTS
        if item["priority"] == "must" and item["status"] == "deferred"
    ]
    assert deferred_must == []


def test_unimplemented_shoulds_are_deferred_and_backlogged() -> None:
    backlog_ids = {item["id"] for item in BACKLOG}
    backlog_sources = {item["source"] for item in BACKLOG}
    deferred = deferred_requirements()
    assert {item["id"] for item in deferred} == {"FR-ORG-005", "FR-IMP-010"}
    for item in deferred:
        assert item["priority"] == "should"
        backlog_id = item.get("backlog_id")
        assert backlog_id in backlog_ids
        assert item["id"] in backlog_sources
        assert item.get("deferred_reason")


def test_agent_cannot_accept_security_data_or_cost_risks() -> None:
    for risk in RISKS:
        accepted_by = (risk.get("accepted_by") or "").strip().lower()
        if not accepted_by:
            continue
        if risk["category"] in PROTECTED_ACCEPTANCE_CATEGORIES:
            assert accepted_by not in AGENT_ACCEPTANCE_VALUES, risk["id"]
            assert risk.get("accepted_on"), risk["id"]


def test_realized_risks_have_an_incident_and_regression() -> None:
    for risk in RISKS:
        if not risk.get("realized"):
            continue
        assert risk.get("incident"), risk["id"]
        regression = risk.get("regression_evidence")
        assert regression
        assert evidence_exists(regression)


def test_documentation_lists_every_stable_id() -> None:
    text = _docs_text()
    required = [
        *expected_functional_ids(),
        *expected_nfr_ids(),
        *expected_acceptance_ids(),
        *expected_gate_ids(),
        *expected_risk_ids(),
        *[f"Plan {plan_id}" for plan_id in expected_plan_ids()],
    ]
    missing = [item_id for item_id in required if item_id not in text]
    assert missing == []
    for path in DOC_PATHS:
        assert path.is_file(), path.relative_to(REPO_ROOT)
        assert "spec-docs" not in path.read_text(encoding="utf-8")
