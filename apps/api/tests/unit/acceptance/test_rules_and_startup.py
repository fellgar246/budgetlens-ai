from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from budgetlens.adapters.db import reset_engine
from budgetlens.config import reset_settings_cache
from budgetlens.domain.enums import AccountType, Favorability, VarianceState
from budgetlens.domain.money import MoneyAmount
from budgetlens.domain.tools import default_tool_registry
from budgetlens.domain.variance import compute_variance
from budgetlens.presentation.app import create_app

REPO_ROOT = Path(__file__).resolve().parents[5]


def test_zero_budget_nonzero_actual_is_unbounded() -> None:
    result = compute_variance(
        actual_amount=MoneyAmount("25"),
        budget_amount=MoneyAmount("0"),
        account_type=AccountType.EXPENSE,
    )
    assert result.variance_amount.as_text() == "25.0000"
    assert result.variance_percent is None
    assert result.variance_state is VarianceState.UNBOUNDED


def test_expense_over_budget_is_unfavorable() -> None:
    result = compute_variance(
        actual_amount=MoneyAmount("120"),
        budget_amount=MoneyAmount("100"),
        account_type=AccountType.EXPENSE,
    )
    assert result.variance_amount.as_text() == "20.0000"
    assert result.favorability is Favorability.UNFAVORABLE


def test_revenue_over_budget_is_favorable() -> None:
    result = compute_variance(
        actual_amount=MoneyAmount("120"),
        budget_amount=MoneyAmount("100"),
        account_type=AccountType.REVENUE,
    )
    assert result.variance_amount.as_text() == "20.0000"
    assert result.favorability is Favorability.FAVORABLE


def test_no_mutable_copilot_tools_are_registered() -> None:
    names = default_tool_registry().names()
    assert "apply_import" not in names
    assert "execute_sql" not in names
    assert "run_query" not in names


def test_create_app_rejects_dev_auth_in_prod_before_serving(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://budgetlens:x@localhost:5432/budgetlens",
    )
    reset_settings_cache()
    reset_engine()
    with pytest.raises(ValidationError):
        create_app()


def test_local_stack_files_name_web_api_and_postgres() -> None:
    compose = (REPO_ROOT / "compose.yaml").read_text(encoding="utf-8")
    bootstrap = (REPO_ROOT / "scripts" / "bootstrap.sh").read_text(encoding="utf-8")
    assert "postgres:" in compose
    assert "api:" in compose
    assert "web:" in compose
    assert "worker:" in compose
    assert "uv sync" in bootstrap
    assert (REPO_ROOT / "scripts" / "acceptance-local-stack.sh").is_file()
