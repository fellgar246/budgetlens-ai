from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = REPO_ROOT / "scripts"
OPERATIONS = REPO_ROOT / "docs" / "OPERATIONS.md"
WORKFLOWS = REPO_ROOT / ".github" / "workflows"


def _load(name: str) -> ModuleType:
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_operations_documents_daily_cost_scaling_and_runbooks() -> None:
    text = OPERATIONS.read_text(encoding="utf-8")
    for heading in (
        "## Daily checklist",
        "## Cost and account guardrails",
        "## Development policy",
        "## Backups",
        "## Runbooks",
        "## Scaling",
        "### Deploy and rollback",
        "### Database migration failure",
        "### Restore database",
        "### Bedrock unavailable or throttled",
        "### Import job stuck",
        "### S3 access denied",
        "### Secret rotation",
        "### Cognito login incident",
        "### Unexpected cost spike",
        "### Teardown",
    ):
        assert heading in text, heading
    assert "99.5%" in text
    assert "A budget is an alert, not a hard cap" in text
    assert "synthetic" in text.lower()
    assert "Redis" in text
    assert "ADR" in text
    assert "calculator.aws" in text
    assert "Do not invent a price" in text
    assert "DISABLE_DELETION_PROTECTION=1" in text
    assert "EMPTY_BUCKET" in text
    assert "APPLY_DESTROY=1" in text
    assert "state bucket" in text.lower()


def test_cost_estimate_script_records_human_official_figures_only() -> None:
    estimate = _load("record_cost_estimate")
    sizes = estimate.load_environment_sizes("dev")
    assert sizes["api_desired_count"] == 1
    assert sizes["db_multi_az"] is False
    assert sizes["nat_gateway_count"] == 1
    record = estimate.build_record(
        environment="dev",
        source="https://calculator.aws/#estimate",
        monthly_estimate="42.00",
        sizes=sizes,
        recorded_at="2026-09-01",
    )
    assert record["estimate"] is True
    assert record["monthly_estimate"] == "42.00"
    estimate.check_record(record, sizes)
    with pytest.raises(ValueError, match="official"):
        estimate.build_record(
            environment="dev",
            source="https://example.com/guess",
            monthly_estimate="42",
            sizes=sizes,
        )
    with pytest.raises(ValueError, match="invent"):
        estimate.build_record(
            environment="dev",
            source="https://calculator.aws/#estimate",
            monthly_estimate="",
            sizes=sizes,
        )
    drifted = dict(sizes)
    drifted["api_desired_count"] = 8
    with pytest.raises(ValueError, match="sizes changed"):
        estimate.check_record(record, drifted)


def test_cost_estimate_print_sizes_does_not_invent_a_price() -> None:
    estimate = _load("record_cost_estimate")
    assert estimate.main(["--print-sizes", "--environment", "dev"]) == 0
    with pytest.raises(SystemExit):
        estimate.main(["--environment", "dev"])


def test_teardown_script_refuses_unconfirmed_and_state_destroy() -> None:
    text = (SCRIPTS / "teardown-environment.sh").read_text(encoding="utf-8")
    assert text.startswith("#!/bin/sh")
    assert "CONFIRM" in text
    assert "CONFIRM_PROD" in text
    assert "get-caller-identity" in text
    assert "DISABLE_DELETION_PROTECTION" in text
    assert "EMPTY_BUCKET" in text
    assert "APPLY_DESTROY" in text
    assert "bootstrap" in text
    assert "state bucket" in text.lower()
    assert "apply -auto-approve" not in text
    assert "never -auto-approve" in text
    snapshot = (SCRIPTS / "snapshot-db.sh").read_text(encoding="utf-8")
    assert snapshot.startswith("#!/bin/sh")
    assert "create-db-snapshot" in snapshot
    assert "password" not in snapshot.lower()


def test_terraform_plan_prints_visible_sizes_not_a_price() -> None:
    text = (WORKFLOWS / "terraform-plan.yml").read_text(encoding="utf-8")
    assert "record_cost_estimate.py" in text
    assert "Visible cost sizes" in text
    assert "not a hard cap" in text


def test_makefile_exposes_cost_estimate_and_dev_teardown() -> None:
    text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    assert "record-cost-estimate" in text
    assert "teardown-dev" in text
    assert "teardown-environment.sh" in text
