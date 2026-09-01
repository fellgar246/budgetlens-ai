from __future__ import annotations

from budgetlens.adapters.ai import DeterministicAIProvider
from budgetlens.application.ai_eval import run_stub_eval


def test_stub_eval_dataset_passes(env_settings: None) -> None:
    del env_settings
    result = run_stub_eval(DeterministicAIProvider())
    assert result["passed"] == result["total"]
    assert result["total"] == 18
    gates = result["gates"]
    assert isinstance(gates, dict)
    assert gates["safety"] is True
    assert gates["critical_numeric"] is True
    assert gates["global"] is True
