# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false
from __future__ import annotations

from typing import Any, cast

from budgetlens.application.pagination import ABSOLUTE_MAX_LIMIT, MAX_LIMIT
from budgetlens.presentation.app import create_app


def _as_dict(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in cast(dict[object, object], value).items()}


def test_page_limit_stays_at_or_below_absolute_max() -> None:
    assert MAX_LIMIT <= ABSOLUTE_MAX_LIMIT
    assert ABSOLUTE_MAX_LIMIT == 500


def test_list_endpoints_require_pagination_or_small_caps(env_settings: None) -> None:
    del env_settings
    spec = _as_dict(create_app().openapi())
    unbounded: list[str] = []
    paths = _as_dict(spec.get("paths"))
    schemas = _as_dict(_as_dict(spec.get("components")).get("schemas"))
    for path, raw_methods in paths.items():
        methods = _as_dict(raw_methods)
        for method, raw_operation in methods.items():
            if method not in {"get", "post"}:
                continue
            operation = _as_dict(raw_operation)
            responses = _as_dict(operation.get("responses"))
            success = responses.get("200") or responses.get("201")
            if not isinstance(success, dict):
                continue
            json_content = _as_dict(_as_dict(success).get("content")).get("application/json")
            schema = _as_dict(json_content).get("schema")
            ref = _as_dict(schema).get("$ref")
            if not isinstance(ref, str):
                continue
            name = ref.rsplit("/", 1)[-1]
            properties = _as_dict(_as_dict(schemas.get(name)).get("properties"))
            if "items" not in properties:
                continue
            has_page = "page" in properties
            parameters = operation.get("parameters", [])
            maximum: object = None
            if isinstance(parameters, list):
                for item in parameters:
                    param = _as_dict(item)
                    if param.get("name") == "limit":
                        maximum = _as_dict(param.get("schema")).get("maximum")
            if not has_page and maximum is None:
                unbounded.append(f"{method.upper()} {path}")
            if isinstance(maximum, int):
                assert maximum <= 500, f"{path} allows more than 500 rows"
    assert unbounded == []
