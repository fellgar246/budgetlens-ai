from __future__ import annotations

from budgetlens.application.ai_eval import run_stub_eval


def test_stub_eval_dataset_passes(env_settings: None) -> None:
    del env_settings
    result = run_stub_eval()
    assert result["passed"] == result["total"]
    assert result["total"] == 7
