from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

from budgetlens.domain.enums import Permission
from budgetlens.domain.errors import ValidationError, field_issue

FORBIDDEN_TOOLS = frozenset(
    {
        "run_query",
        "execute_sql",
        "fetch_url",
        "read_file",
        "send_email",
        "apply_import",
    }
)

_SCOPE_PROPERTIES: dict[str, Any] = {
    "fiscal_year": {"type": "integer"},
    "period_from": {"type": "string"},
    "period_to": {"type": "string"},
    "budget_version_id": {"type": "string"},
    "account_ids": {"type": "array", "items": {"type": "string"}},
    "department_ids": {"type": "array", "items": {"type": "string"}},
    "cost_center_ids": {"type": "array", "items": {"type": "string"}},
}

_RULE_SCOPE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["period_from", "period_to"],
    "properties": {
        "period_from": {"type": "string"},
        "period_to": {"type": "string"},
        "account_ids": {"type": "array", "items": {"type": "string"}},
        "department_ids": {"type": "array", "items": {"type": "string"}},
        "cost_center_ids": {"type": "array", "items": {"type": "string"}},
    },
}


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    permissions: frozenset[Permission]
    row_budget: int
    label: str


class ToolRegistry:
    def __init__(self, tools: Sequence[ToolDefinition]) -> None:
        names = [item.name for item in tools]
        if len(names) != len(set(names)):
            raise ValidationError("DUPLICATE_TOOL", "El registro de herramientas está duplicado.")
        forbidden = FORBIDDEN_TOOLS.intersection(names)
        if forbidden:
            raise ValidationError(
                "FORBIDDEN_TOOL",
                "El registro no admite herramientas de mutación o acceso libre.",
            )
        self._tools = {item.name: item for item in tools}

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def require(self, name: str) -> ToolDefinition:
        tool = self.get(name)
        if tool is None:
            raise ValidationError(
                "UNKNOWN_TOOL",
                "La herramienta solicitada no está registrada.",
            )
        return tool

    def names(self) -> frozenset[str]:
        return frozenset(self._tools)

    def definitions(self) -> tuple[ToolDefinition, ...]:
        return tuple(self._tools.values())

    def validate_arguments(self, name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        tool = self.require(name)
        payload = {str(key): value for key, value in arguments.items()}
        payload.pop("organization_id", None)
        return validate_closed_schema(tool.input_schema, payload, field=name)

    def bedrock_specs(self) -> tuple[dict[str, Any], ...]:
        return tuple(
            {
                "toolSpec": {
                    "name": item.name,
                    "description": item.description,
                    "inputSchema": {"json": item.input_schema},
                }
            }
            for item in self._tools.values()
        )


def validate_closed_schema(schema: Mapping[str, Any], value: object, *, field: str) -> Any:
    expected = schema.get("type")
    if expected == "object":
        if not isinstance(value, dict):
            raise ValidationError(
                "INVALID_TOOL_ARGS",
                "Los argumentos de la herramienta no son válidos.",
                field_errors=[field_issue(field, "INVALID_TOOL_ARGS", "Se esperaba un objeto.")],
            )
        raw = {str(key): item for key, item in cast(dict[object, object], value).items()}
        properties = _as_schema_map(schema.get("properties"))
        if schema.get("additionalProperties") is False:
            extra = set(raw) - set(properties)
            if extra:
                raise ValidationError(
                    "INVALID_TOOL_ARGS",
                    "Los argumentos de la herramienta no son válidos.",
                    field_errors=[
                        field_issue(field, "INVALID_TOOL_ARGS", "Hay propiedades no permitidas.")
                    ],
                )
        cleaned: dict[str, Any] = {}
        for key, item_schema in properties.items():
            if key not in raw:
                continue
            cleaned[key] = validate_closed_schema(item_schema, raw[key], field=f"{field}.{key}")
        for required in _as_str_list(schema.get("required")):
            if required not in cleaned:
                raise ValidationError(
                    "INVALID_TOOL_ARGS",
                    "Los argumentos de la herramienta no son válidos.",
                    field_errors=[
                        field_issue(
                            f"{field}.{required}",
                            "INVALID_TOOL_ARGS",
                            "Falta un argumento obligatorio.",
                        )
                    ],
                )
        return cleaned
    if expected == "array":
        if not isinstance(value, list):
            raise ValidationError(
                "INVALID_TOOL_ARGS",
                "Los argumentos de la herramienta no son válidos.",
                field_errors=[field_issue(field, "INVALID_TOOL_ARGS", "Se esperaba una lista.")],
            )
        item_schema = _as_schema_map(schema.get("items"))
        return [
            validate_closed_schema(item_schema, item, field=f"{field}[{index}]")
            for index, item in enumerate(cast(list[object], value))
        ]
    if expected == "string":
        if not isinstance(value, str):
            raise ValidationError(
                "INVALID_TOOL_ARGS",
                "Los argumentos de la herramienta no son válidos.",
                field_errors=[field_issue(field, "INVALID_TOOL_ARGS", "Se esperaba texto.")],
            )
        _assert_enum(schema, value, field=field)
        return value
    if expected == "integer":
        if type(value) is bool or not isinstance(value, int):
            raise ValidationError(
                "INVALID_TOOL_ARGS",
                "Los argumentos de la herramienta no son válidos.",
                field_errors=[field_issue(field, "INVALID_TOOL_ARGS", "Se esperaba un entero.")],
            )
        _assert_enum(schema, value, field=field)
        _assert_bounds(schema, value, field=field)
        return value
    if expected == "number":
        if type(value) is bool or not isinstance(value, int | float):
            raise ValidationError(
                "INVALID_TOOL_ARGS",
                "Los argumentos de la herramienta no son válidos.",
                field_errors=[field_issue(field, "INVALID_TOOL_ARGS", "Se esperaba un número.")],
            )
        number = float(value)
        _assert_bounds(schema, number, field=field)
        return number
    return value


def _assert_enum(schema: Mapping[str, Any], value: object, *, field: str) -> None:
    allowed = schema.get("enum")
    if allowed is None:
        return
    if value not in cast(list[object], allowed):
        raise ValidationError(
            "INVALID_TOOL_ARGS",
            "Los argumentos de la herramienta no son válidos.",
            field_errors=[field_issue(field, "INVALID_TOOL_ARGS", "El valor no está permitido.")],
        )


def _assert_bounds(schema: Mapping[str, Any], value: int | float, *, field: str) -> None:
    minimum = schema.get("minimum")
    maximum = schema.get("maximum")
    if isinstance(minimum, int | float) and value < minimum:
        raise ValidationError(
            "INVALID_TOOL_ARGS",
            "Los argumentos de la herramienta no son válidos.",
            field_errors=[
                field_issue(field, "INVALID_TOOL_ARGS", "El valor está por debajo del mínimo.")
            ],
        )
    if isinstance(maximum, int | float) and value > maximum:
        raise ValidationError(
            "INVALID_TOOL_ARGS",
            "Los argumentos de la herramienta no son válidos.",
            field_errors=[field_issue(field, "INVALID_TOOL_ARGS", "El valor excede el máximo.")],
        )


def _as_schema_map(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in cast(dict[object, object], value).items()}


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in cast(list[object], value)]


def _object_schema(
    properties: dict[str, Any], *, required: list[str] | None = None
) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
    }
    if required:
        schema["required"] = required
    return schema


def built_in_tools() -> tuple[ToolDefinition, ...]:
    return (
        ToolDefinition(
            name="get_variance_summary",
            description=(
                "Return authorized budget, actual, variance, percent, favorability, and currency."
            ),
            input_schema=_object_schema(_SCOPE_PROPERTIES),
            permissions=frozenset({Permission.READ_ANALYSIS, Permission.USE_AI}),
            row_budget=1,
            label="Resumen de variación",
        ),
        ToolDefinition(
            name="get_variance_breakdown",
            description="Return an aggregated variance breakdown, sorted and limited.",
            input_schema=_object_schema(
                {
                    **_SCOPE_PROPERTIES,
                    "group_by": {
                        "type": "string",
                        "enum": ["account", "department", "cost_center", "period"],
                    },
                    "sort": {
                        "type": "string",
                        "enum": [
                            "variance_amount",
                            "absolute_variance",
                            "budget_amount",
                            "actual_amount",
                        ],
                    },
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                }
            ),
            permissions=frozenset({Permission.READ_ANALYSIS, Permission.USE_AI}),
            row_budget=20,
            label="Desglose",
        ),
        ToolDefinition(
            name="get_top_unfavorable_variances",
            description=(
                "Return the largest unfavorable variances with contribution when definable."
            ),
            input_schema=_object_schema(
                {
                    **_SCOPE_PROPERTIES,
                    "group_by": {
                        "type": "string",
                        "enum": ["account", "department", "cost_center", "period"],
                    },
                    "limit": {"type": "integer", "minimum": 1, "maximum": 10},
                }
            ),
            permissions=frozenset({Permission.READ_ANALYSIS, Permission.USE_AI}),
            row_budget=10,
            label="Principales desfavorables",
        ),
        ToolDefinition(
            name="compare_periods",
            description="Compare two non-overlapping authorized period ranges.",
            input_schema=_object_schema(
                {
                    **_SCOPE_PROPERTIES,
                    "compare_from": {"type": "string"},
                    "compare_to": {"type": "string"},
                }
            ),
            permissions=frozenset({Permission.READ_ANALYSIS, Permission.USE_AI}),
            row_budget=2,
            label="Comparación de periodos",
        ),
        ToolDefinition(
            name="calculate_scenario_preview",
            description="Preview validated scenario rules against a baseline without saving.",
            input_schema=_object_schema(
                {
                    **_SCOPE_PROPERTIES,
                    "baseline_type": {"type": "string", "enum": ["budget", "actual"]},
                    "rules": {
                        "type": "array",
                        "items": _object_schema(
                            {
                                "operation": {
                                    "type": "string",
                                    "enum": ["percentage_change", "absolute_change"],
                                },
                                "value": {"type": "string"},
                                "sequence": {"type": "integer"},
                                "scope": _RULE_SCOPE_SCHEMA,
                            },
                            required=["operation", "value", "scope"],
                        ),
                    },
                }
            ),
            permissions=frozenset({Permission.READ_ANALYSIS, Permission.USE_AI}),
            row_budget=50,
            label="Vista previa de escenario",
        ),
    )


def default_tool_registry() -> ToolRegistry:
    return ToolRegistry(built_in_tools())
