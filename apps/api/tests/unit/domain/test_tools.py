from __future__ import annotations

import pytest

from budgetlens.domain.errors import ValidationError
from budgetlens.domain.tools import FORBIDDEN_TOOLS, default_tool_registry


def test_registry_is_closed_and_rejects_forbidden_tools() -> None:
    registry = default_tool_registry()
    assert "run_query" not in registry.names()
    assert FORBIDDEN_TOOLS.isdisjoint(registry.names())
    with pytest.raises(ValidationError) as exc:
        registry.require("execute_sql")
    assert exc.value.code == "UNKNOWN_TOOL"


def test_tool_schemas_reject_extra_properties_and_organization_id() -> None:
    registry = default_tool_registry()
    cleaned = registry.validate_arguments(
        "get_variance_summary",
        {"fiscal_year": 2026, "organization_id": "should-be-dropped"},
    )
    assert cleaned == {"fiscal_year": 2026}
    with pytest.raises(ValidationError) as exc:
        registry.validate_arguments("get_variance_breakdown", {"group_by": "vendor"})
    assert exc.value.code == "INVALID_TOOL_ARGS"
    with pytest.raises(ValidationError):
        registry.validate_arguments("get_top_unfavorable_variances", {"limit": 50})


def test_bedrock_specs_are_closed() -> None:
    for spec in default_tool_registry().bedrock_specs():
        schema = spec["toolSpec"]["inputSchema"]["json"]
        assert schema["additionalProperties"] is False
