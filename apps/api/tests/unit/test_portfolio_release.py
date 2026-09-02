from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from budgetlens.adapters.ai import DeterministicAIProvider
from budgetlens.application.ai_eval import EVAL_CASES, run_stub_eval

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = REPO_ROOT / "scripts"
DOCS = REPO_ROOT / "docs"


def _load(name: str) -> ModuleType:
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_portfolio_documents_and_sample_data_exist() -> None:
    portfolio = _load("portfolio_release")
    assert portfolio.missing_docs() == []
    sample = REPO_ROOT / "sample-data"
    for name in (
        "budget-valid.csv",
        "actuals-valid.csv",
        "invalid-row.csv",
        "formula.xlsx",
        "README.md",
    ):
        assert (sample / name).is_file(), name


def test_portfolio_check_passes_on_the_repository() -> None:
    portfolio = _load("portfolio_release")
    assert portfolio.check_portfolio() == []
    assert portfolio.application_version() == "0.1.0"
    assert portfolio.main(["--print-checklist"]) == 0
    assert portfolio.main(["--check"]) == 0


def test_release_tag_is_refused_without_production_gates() -> None:
    portfolio = _load("portfolio_release")
    with pytest.raises(ValueError, match="blocked"):
        portfolio.refuse_release_tag()
    with pytest.raises(SystemExit, match="blocked"):
        portfolio.main(["--tag"])


def test_ai_evaluation_summary_is_an_aggregate_without_case_prompts(
    env_settings: None,
) -> None:
    del env_settings
    text = (DOCS / "AI_EVALUATION.md").read_text(encoding="utf-8")
    assert "20 / 20" in text
    assert "not claimed" in text
    for case in EVAL_CASES:
        assert case.id in text
        assert case.prompt not in text
    result = run_stub_eval(DeterministicAIProvider())
    assert result["passed"] == result["total"]
    assert result["total"] == 20
    gates = result["gates"]
    assert isinstance(gates, dict)
    assert gates["safety"] is True
    assert gates["critical_numeric"] is True
    assert gates["global"] is True


def test_cost_page_matches_terraform_sizes_and_refuses_a_price() -> None:
    portfolio = _load("portfolio_release")
    estimate = _load("record_cost_estimate")
    cost = (DOCS / "COST.md").read_text(encoding="utf-8")
    sizes = estimate.load_environment_sizes("dev")
    assert sizes["nat_gateway_count"] == 1
    assert sizes["api_desired_count"] == 1
    assert sizes["db_instance_class"] == "db.t4g.micro"
    assert sizes["ai_provider"] == "stub"
    assert str(sizes["db_instance_class"]) in cost
    assert "Do not invent a monthly price" in cost
    assert "monthly_estimate" not in cost
    assert portfolio.secret_hits(cost) == []


def test_architecture_and_demo_stay_reproducible() -> None:
    architecture = (DOCS / "ARCHITECTURE.md").read_text(encoding="utf-8")
    demo = (DOCS / "DEMO.md").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "```mermaid" in architecture
    assert "ECS Fargate" in architecture
    assert "make seed" in demo
    assert "Ana Analyst" in demo
    assert "docs/DEMO.md" in readme
    assert "docs/RELEASE.md" in readme
    assert "local portfolio" in readme.lower() or "portfolio demo" in readme.lower()
