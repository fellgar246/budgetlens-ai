# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, cast

from budgetlens.presentation.app import create_app
from budgetlens.presentation.openapi import OPERATIONS

SNAPSHOT = Path(__file__).resolve().parents[4] / "packages" / "api-client" / "openapi.json"
CLIENT = Path(__file__).resolve().parents[4] / "packages" / "api-client" / "src" / "index.ts"
PATH_TEMPLATE = re.compile(r"API_PREFIX\}/([^`\"'?]+)")
CAMEL = re.compile(r"(?<!^)(?=[A-Z])")
HTTP_METHODS = {"get", "put", "post", "delete", "patch"}
PARAM = re.compile(r"\{[^}]+\}")

REQUIRED_CONTRACT_PATHS = {
    ("GET", "/api/v1/health/live"),
    ("GET", "/api/v1/health/ready"),
    ("GET", "/api/v1/version"),
    ("GET", "/api/v1/me"),
    ("GET", "/api/v1/organizations"),
    ("POST", "/api/v1/organizations"),
    ("GET", "/api/v1/organizations/{organization_id}"),
    ("PATCH", "/api/v1/organizations/{organization_id}"),
    ("GET", "/api/v1/memberships"),
    ("POST", "/api/v1/memberships"),
    ("PATCH", "/api/v1/memberships/{membership_id}"),
    ("GET", "/api/v1/accounts"),
    ("POST", "/api/v1/accounts"),
    ("GET", "/api/v1/accounts/{account_id}"),
    ("PATCH", "/api/v1/accounts/{account_id}"),
    ("GET", "/api/v1/departments"),
    ("POST", "/api/v1/departments"),
    ("GET", "/api/v1/departments/{department_id}"),
    ("PATCH", "/api/v1/departments/{department_id}"),
    ("GET", "/api/v1/cost-centers"),
    ("POST", "/api/v1/cost-centers"),
    ("GET", "/api/v1/cost-centers/{cost_center_id}"),
    ("PATCH", "/api/v1/cost-centers/{cost_center_id}"),
    ("GET", "/api/v1/budget-versions"),
    ("POST", "/api/v1/budget-versions"),
    ("GET", "/api/v1/budget-versions/{version_id}"),
    ("PATCH", "/api/v1/budget-versions/{version_id}"),
    ("POST", "/api/v1/budget-versions/{version_id}/publish"),
    ("POST", "/api/v1/budget-versions/{version_id}/activate"),
    ("POST", "/api/v1/budget-versions/{version_id}/archive"),
    ("POST", "/api/v1/imports"),
    ("PUT", "/api/v1/imports/{job_id}/content"),
    ("POST", "/api/v1/imports/{job_id}/validate"),
    ("GET", "/api/v1/imports/{job_id}"),
    ("GET", "/api/v1/imports/{job_id}/preview"),
    ("GET", "/api/v1/imports/{job_id}/errors"),
    ("POST", "/api/v1/imports/{job_id}/commit"),
    ("POST", "/api/v1/imports/{job_id}/cancel"),
    ("GET", "/api/v1/analytics/variance-summary"),
    ("GET", "/api/v1/analytics/variance-breakdown"),
    ("GET", "/api/v1/analytics/top-unfavorable"),
    ("GET", "/api/v1/analytics/compare-periods"),
    ("POST", "/api/v1/exports"),
    ("GET", "/api/v1/scenarios"),
    ("POST", "/api/v1/scenarios"),
    ("GET", "/api/v1/scenarios/{scenario_id}"),
    ("PATCH", "/api/v1/scenarios/{scenario_id}"),
    ("POST", "/api/v1/scenarios/preview"),
    ("POST", "/api/v1/scenarios/{scenario_id}/archive"),
    ("GET", "/api/v1/conversations"),
    ("POST", "/api/v1/conversations"),
    ("GET", "/api/v1/conversations/{conversation_id}"),
    ("DELETE", "/api/v1/conversations/{conversation_id}"),
    ("GET", "/api/v1/conversations/{conversation_id}/messages"),
    ("POST", "/api/v1/conversations/{conversation_id}/messages"),
    ("GET", "/api/v1/audit-events"),
}

IDEMPOTENT_OPERATIONS = {
    "publish_budget_version",
    "activate_budget_version",
    "archive_budget_version",
    "commit_import",
}


def _as_dict(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in cast(dict[object, object], value).items()}


def _snake(value: str) -> str:
    return CAMEL.sub("_", value).lower()


def _normalize(path: str) -> str:
    return PARAM.sub("{}", path.rstrip("/"))


def _client_paths() -> set[str]:
    found: set[str] = set()
    for raw in PATH_TEMPLATE.findall(CLIENT.read_text(encoding="utf-8")):
        path = "/api/v1/" + raw
        path = re.sub(r"\$\{([^}]+)\}", lambda match: "{" + _snake(match.group(1)) + "}", path)
        found.add(_normalize(path))
    return found


def _operations(spec: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    items: list[tuple[str, str, dict[str, Any]]] = []
    for path, raw_methods in _as_dict(spec.get("paths")).items():
        for method, raw_operation in _as_dict(raw_methods).items():
            if method not in HTTP_METHODS:
                continue
            items.append((method.upper(), path, _as_dict(raw_operation)))
    return items


def test_openapi_snapshot_matches_application(env_settings: None) -> None:
    del env_settings
    generated = create_app().openapi()
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert generated == snapshot


def test_typescript_client_paths_exist_in_the_snapshot() -> None:
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    documented = {_normalize(path) for path in snapshot.get("paths", {})}
    missing = sorted(path for path in _client_paths() if path not in documented)
    assert missing == []


def test_contract_paths_are_documented_and_covered_by_the_client(env_settings: None) -> None:
    del env_settings
    spec = create_app().openapi()
    documented = {
        (method, _normalize(path)) for method, path, _operation in _operations(_as_dict(spec))
    }
    required = {(method, _normalize(path)) for method, path in REQUIRED_CONTRACT_PATHS}
    missing = sorted(
        f"{method} {path}" for method, path in required if (method, path) not in documented
    )
    assert missing == []
    client_paths = _client_paths()
    uncovered = sorted(f"{method} {path}" for method, path in required if path not in client_paths)
    assert uncovered == []


def test_operation_ids_are_stable_unique_and_documented(env_settings: None) -> None:
    del env_settings
    spec = create_app().openapi()
    ids: list[str] = []
    missing_permission: list[str] = []
    missing_errors: list[str] = []
    generated: list[str] = []
    for method, path, operation in _operations(_as_dict(spec)):
        operation_id = str(operation.get("operationId") or "")
        ids.append(operation_id)
        if "_api_v1_" in operation_id or not operation_id:
            generated.append(f"{method} {path}")
        if "x-permission" not in operation:
            missing_permission.append(f"{method} {path}")
        responses = _as_dict(operation.get("responses"))
        if (
            "401" in _as_dict(operation.get("responses"))
            or operation.get("x-permission") == "public"
        ):
            pass
        contract = OPERATIONS.get(operation_id)
        if contract is not None:
            for status in contract.errors:
                if str(status) not in responses:
                    missing_errors.append(f"{method} {path} {status}")
            if contract.idempotent:
                parameters = operation.get("parameters", [])
                required = False
                if isinstance(parameters, list):
                    for item in parameters:
                        param = _as_dict(item)
                        if param.get("name") == "Idempotency-Key" and param.get("required") is True:
                            required = True
                if not required:
                    missing_errors.append(f"{method} {path} missing required Idempotency-Key")
    assert generated == []
    assert missing_permission == []
    assert missing_errors == []
    assert len(ids) == len(set(ids))
    assert set(IDEMPOTENT_OPERATIONS) <= set(ids)


def test_error_envelope_and_trace_header_are_declared(env_settings: None) -> None:
    del env_settings
    spec = _as_dict(create_app().openapi())
    schemas = _as_dict(_as_dict(spec.get("components")).get("schemas"))
    assert "ErrorEnvelope" in schemas
    envelope = _as_dict(schemas["ErrorEnvelope"])
    assert "error" in _as_dict(envelope.get("properties"))
    assert "trace_id" in _as_dict(envelope.get("properties"))
    for method, path, operation in _operations(spec):
        responses = _as_dict(operation.get("responses"))
        for status, raw_response in responses.items():
            response = _as_dict(raw_response)
            headers = _as_dict(response.get("headers"))
            assert "X-Trace-Id" in headers, f"{method} {path} {status}"
        if "400" in responses:
            content = _as_dict(_as_dict(responses["400"]).get("content"))
            json_content = _as_dict(content.get("application/json"))
            ref = _as_dict(json_content.get("schema")).get("$ref")
            assert ref == "#/components/schemas/ErrorEnvelope", f"{method} {path}"


def test_schema_properties_use_snake_case(env_settings: None) -> None:
    del env_settings
    spec = _as_dict(create_app().openapi())
    schemas = _as_dict(_as_dict(spec.get("components")).get("schemas"))
    offenders: list[str] = []
    for name, raw_schema in schemas.items():
        properties = _as_dict(_as_dict(raw_schema).get("properties"))
        for key in properties:
            if key != key.lower() or "-" in key:
                offenders.append(f"{name}.{key}")
    assert offenders == []
