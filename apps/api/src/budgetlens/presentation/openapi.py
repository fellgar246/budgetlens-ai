# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast


@dataclass(frozen=True, slots=True)
class OperationContract:
    permission: str
    errors: tuple[int, ...]
    summary: str
    idempotent: bool = False


ERROR_STATUSES = {
    400: "Malformed request",
    401: "Not authenticated",
    403: "Authenticated without permission",
    404: "Not found or hidden cross-tenant resource",
    409: "Conflict, concurrency, or idempotency mismatch",
    413: "Upload too large",
    422: "Semantic validation failed",
    429: "Rate limited",
    503: "Dependency unavailable",
}

ERROR_ENVELOPE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["error", "trace_id"],
    "properties": {
        "error": {
            "type": "object",
            "additionalProperties": False,
            "required": ["code", "message", "field_errors", "retryable"],
            "properties": {
                "code": {"type": "string", "examples": ["IMPORT_VALIDATION_FAILED"]},
                "message": {
                    "type": "string",
                    "examples": ["El archivo contiene errores que deben corregirse."],
                },
                "field_errors": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["code", "message"],
                        "properties": {
                            "field": {"type": "string", "examples": ["period"]},
                            "code": {"type": "string", "examples": ["INVALID_PERIOD"]},
                            "message": {"type": "string", "examples": ["Periodo inválido."]},
                        },
                    },
                },
                "retryable": {"type": "boolean", "examples": [False]},
            },
        },
        "trace_id": {"type": "string", "examples": ["01HZX4EXAMPLETRACE"]},
    },
    "examples": [
        {
            "error": {
                "code": "IMPORT_VALIDATION_FAILED",
                "message": "El archivo contiene errores que deben corregirse.",
                "field_errors": [
                    {
                        "field": "period",
                        "code": "INVALID_PERIOD",
                        "message": "Periodo inválido.",
                    }
                ],
                "retryable": False,
            },
            "trace_id": "01HZX4EXAMPLETRACE",
        }
    ],
}

TRACE_HEADER = {
    "X-Trace-Id": {
        "description": "Request correlation identifier.",
        "schema": {"type": "string"},
    }
}

AUTH_ERRORS = (401,)
TENANT_ERRORS = (401, 403, 404)
MUTATION_ERRORS = (400, 401, 403, 404, 422)
CONFLICT_ERRORS = (400, 401, 403, 404, 409, 422)
UPLOAD_ERRORS = (400, 401, 403, 404, 413, 422)
RATE_LIMITED_MUTATION = (400, 401, 403, 404, 422, 429)
IDEMPOTENT_MUTATION = (400, 401, 403, 404, 409, 422)

OPERATIONS: dict[str, OperationContract] = {
    "get_health_live": OperationContract(
        "public", (), "Process liveness. Does not check dependencies."
    ),
    "get_health_ready": OperationContract(
        "public", (503,), "Short-timeout readiness for the database and loaded settings."
    ),
    "get_version": OperationContract("public", (), "Semantic version, commit SHA, and build time."),
    "get_me": OperationContract(
        "authenticated", AUTH_ERRORS, "Current user, preferences, and capabilities."
    ),
    "list_organizations": OperationContract(
        "authenticated",
        AUTH_ERRORS,
        "Memberships of the current user. Does not require X-Organization-Id.",
    ),
    "create_organization": OperationContract(
        "authenticated", MUTATION_ERRORS, "Create an organization when the caller is authorized."
    ),
    "get_organization": OperationContract(
        "membership", TENANT_ERRORS, "Organization detail. Header must match the path."
    ),
    "patch_organization": OperationContract(
        "MANAGE_ORGANIZATION", CONFLICT_ERRORS, "Admin update. Requires version for concurrency."
    ),
    "list_memberships": OperationContract(
        "membership", TENANT_ERRORS, "Members of the active organization."
    ),
    "create_membership": OperationContract(
        "MANAGE_MEMBERS", MUTATION_ERRORS, "Invite or attach a member."
    ),
    "patch_membership": OperationContract(
        "MANAGE_MEMBERS", MUTATION_ERRORS, "Change role or disable a member. No physical delete."
    ),
    "list_accounts": OperationContract(
        "membership", TENANT_ERRORS, "Account catalog with status, search, and cursor."
    ),
    "create_account": OperationContract(
        "MANAGE_DIMENSIONS", MUTATION_ERRORS, "Create an account. Codes keep case after trim."
    ),
    "get_account": OperationContract("membership", TENANT_ERRORS, "Account detail."),
    "patch_account": OperationContract(
        "MANAGE_DIMENSIONS", MUTATION_ERRORS, "Update account metadata or status."
    ),
    "list_departments": OperationContract("membership", TENANT_ERRORS, "Department catalog."),
    "create_department": OperationContract(
        "MANAGE_DIMENSIONS", MUTATION_ERRORS, "Create a department."
    ),
    "get_department": OperationContract("membership", TENANT_ERRORS, "Department detail."),
    "patch_department": OperationContract(
        "MANAGE_DIMENSIONS", MUTATION_ERRORS, "Update a department."
    ),
    "list_cost_centers": OperationContract("membership", TENANT_ERRORS, "Cost-center catalog."),
    "create_cost_center": OperationContract(
        "MANAGE_DIMENSIONS", MUTATION_ERRORS, "Create a cost center."
    ),
    "get_cost_center": OperationContract("membership", TENANT_ERRORS, "Cost-center detail."),
    "patch_cost_center": OperationContract(
        "MANAGE_DIMENSIONS", MUTATION_ERRORS, "Update a cost center."
    ),
    "list_budget_versions": OperationContract(
        "membership", TENANT_ERRORS, "Budget versions for a fiscal year."
    ),
    "create_budget_version": OperationContract(
        "MANAGE_VERSIONS", MUTATION_ERRORS, "Create a draft budget version."
    ),
    "get_budget_version": OperationContract("membership", TENANT_ERRORS, "Budget version detail."),
    "patch_budget_version": OperationContract(
        "MANAGE_VERSIONS",
        MUTATION_ERRORS,
        "Draft metadata only. Published versions reject name changes.",
    ),
    "publish_budget_version": OperationContract(
        "MANAGE_VERSIONS",
        IDEMPOTENT_MUTATION,
        "Publish a draft. Requires Idempotency-Key and writes audit.",
        True,
    ),
    "activate_budget_version": OperationContract(
        "MANAGE_VERSIONS",
        IDEMPOTENT_MUTATION,
        "Activate a published version. Requires Idempotency-Key.",
        True,
    ),
    "archive_budget_version": OperationContract(
        "MANAGE_VERSIONS", IDEMPOTENT_MUTATION, "Archive a version. Requires Idempotency-Key.", True
    ),
    "list_imports": OperationContract(
        "IMPORT", TENANT_ERRORS, "Import jobs for the active organization."
    ),
    "create_import": OperationContract(
        "IMPORT", RATE_LIMITED_MUTATION, "Create an import job and return the upload target."
    ),
    "upload_import_content": OperationContract(
        "IMPORT",
        UPLOAD_ERRORS,
        "Local/proxy binary upload. Not used when a presigned URL is returned.",
    ),
    "validate_import": OperationContract(
        "IMPORT", MUTATION_ERRORS, "Validate mapped rows without applying them."
    ),
    "get_import": OperationContract(
        "IMPORT", TENANT_ERRORS, "Import status and summary. Does not return raw rows."
    ),
    "preview_import": OperationContract(
        "IMPORT", TENANT_ERRORS, "Sanitized preview page inside the tenant."
    ),
    "list_import_errors": OperationContract(
        "IMPORT", TENANT_ERRORS, "Paginated validation errors."
    ),
    "download_import_errors": OperationContract(
        "IMPORT", TENANT_ERRORS, "CSV export of import errors."
    ),
    "commit_import": OperationContract(
        "IMPORT", IDEMPOTENT_MUTATION, "Apply a ready import. Requires Idempotency-Key.", True
    ),
    "cancel_import": OperationContract(
        "IMPORT", MUTATION_ERRORS, "Cancel a job that has not been applied."
    ),
    "get_variance_summary": OperationContract(
        "READ_ANALYSIS", TENANT_ERRORS, "Budget versus actuals totals for a scope."
    ),
    "get_variance_breakdown": OperationContract(
        "READ_ANALYSIS",
        TENANT_ERRORS,
        "Paginated variance grouped by period, account, department, or cost center.",
    ),
    "get_top_unfavorable": OperationContract(
        "READ_ANALYSIS", TENANT_ERRORS, "Top unfavorable variances. Limit is at most 20."
    ),
    "create_export": OperationContract(
        "EXPORT", RATE_LIMITED_MUTATION, "Create an authorized, time-limited export job."
    ),
    "download_export": OperationContract(
        "EXPORT", TENANT_ERRORS, "Download export content before expiry."
    ),
    "list_scenarios": OperationContract(
        "CREATE_SCENARIOS", TENANT_ERRORS, "Saved what-if scenarios."
    ),
    "create_scenario": OperationContract(
        "CREATE_SCENARIOS", MUTATION_ERRORS, "Save a scenario. Preview does not persist."
    ),
    "get_scenario": OperationContract(
        "CREATE_SCENARIOS", TENANT_ERRORS, "Scenario detail including rules."
    ),
    "patch_scenario": OperationContract(
        "CREATE_SCENARIOS", MUTATION_ERRORS, "Update a draft scenario."
    ),
    "preview_scenario": OperationContract(
        "CREATE_SCENARIOS", MUTATION_ERRORS, "Compute a scenario without writing financial entries."
    ),
    "archive_scenario": OperationContract(
        "CREATE_SCENARIOS", MUTATION_ERRORS, "Archive a scenario."
    ),
    "list_conversations": OperationContract(
        "USE_AI", TENANT_ERRORS, "Copilot conversations for the current user."
    ),
    "create_conversation": OperationContract(
        "USE_AI", RATE_LIMITED_MUTATION, "Start a copilot conversation."
    ),
    "get_conversation": OperationContract("USE_AI", TENANT_ERRORS, "Conversation metadata."),
    "delete_conversation": OperationContract(
        "USE_AI", TENANT_ERRORS, "Logical delete of a conversation."
    ),
    "create_conversation_message": OperationContract(
        "USE_AI",
        RATE_LIMITED_MUTATION,
        "Ask the copilot. Synchronous in 1.0; streaming would be SSE.",
    ),
    "list_audit_events": OperationContract(
        "MANAGE_ORGANIZATION", TENANT_ERRORS, "Admin audit trail. Sensitive metadata is omitted."
    ),
    "get_ops_metrics": OperationContract(
        "VIEW_TECHNICAL_METRICS", AUTH_ERRORS, "Operator metrics. No amounts or prompts."
    ),
    "list_dev_identities": OperationContract(
        "local_dev", (), "Local/test identity switcher. Disabled outside AUTH_MODE=dev."
    ),
}


def apply_contract(schema: dict[str, Any]) -> dict[str, Any]:
    components = _as_dict(schema.get("components"))
    schemas = _as_dict(components.get("schemas"))
    schemas["ErrorEnvelope"] = ERROR_ENVELOPE_SCHEMA
    security_schemes = _as_dict(components.get("securitySchemes"))
    security_schemes["BearerAuth"] = {"type": "http", "scheme": "bearer"}
    components["schemas"] = schemas
    components["securitySchemes"] = security_schemes
    schema["components"] = components

    paths = _as_dict(schema.get("paths"))
    for path, raw_item in paths.items():
        item = _as_dict(raw_item)
        for method, raw_operation in item.items():
            if method not in {"get", "put", "post", "delete", "patch"}:
                continue
            if not isinstance(raw_operation, dict):
                continue
            operation = _as_dict(raw_operation)
            _apply_operation(str(path), method, operation)
            item[method] = operation
        paths[path] = item
    schema["paths"] = paths
    return schema


def _apply_operation(path: str, method: str, operation: dict[str, Any]) -> None:
    operation_id = str(operation.get("operationId") or "")
    contract = OPERATIONS.get(operation_id)
    permission = contract.permission if contract else "membership"
    errors = contract.errors if contract else TENANT_ERRORS
    if contract is not None:
        operation["summary"] = contract.summary
        operation["description"] = f"{contract.summary} Permission: {permission}." + (
            " Requires Idempotency-Key." if contract.idempotent else ""
        )
        operation["x-permission"] = permission
        if contract.idempotent:
            _require_idempotency_key(operation)
    else:
        operation["x-permission"] = permission
        operation.setdefault("summary", f"{method.upper()} {path}")

    if permission == "public":
        operation["security"] = []
        _set_header_required(operation, "authorization", required=False)
    else:
        operation["security"] = [{"BearerAuth": []}]
        _set_header_required(operation, "authorization", required=True)
        if permission not in {"authenticated", "local_dev", "VIEW_TECHNICAL_METRICS"}:
            _set_header_required(operation, "X-Organization-Id", required=True)

    responses = _as_dict(operation.get("responses"))
    for status in errors:
        key = str(status)
        if key == "503" and path == "/api/v1/health/ready":
            existing = _as_dict(responses.get(key))
            existing.setdefault("description", ERROR_STATUSES[status])
            existing["headers"] = {**TRACE_HEADER, **_as_dict(existing.get("headers"))}
            responses[key] = existing
            continue
        existing = _as_dict(responses.get(key))
        content = _as_dict(existing.get("content"))
        content["application/json"] = {
            "schema": {"$ref": "#/components/schemas/ErrorEnvelope"},
            "example": ERROR_ENVELOPE_SCHEMA["examples"][0],
        }
        existing["description"] = ERROR_STATUSES[status]
        existing["content"] = content
        existing["headers"] = {**TRACE_HEADER, **_as_dict(existing.get("headers"))}
        responses[key] = existing

    for key, raw_response in list(responses.items()):
        if not isinstance(raw_response, dict):
            continue
        response = _as_dict(raw_response)
        response["headers"] = {**TRACE_HEADER, **_as_dict(response.get("headers"))}
        _ensure_success_example(response)
        responses[key] = response
    operation["responses"] = responses
    _ensure_request_example(operation)


def _ensure_request_example(operation: dict[str, Any]) -> None:
    raw_body = operation.get("requestBody")
    if not isinstance(raw_body, dict):
        return
    body = _as_dict(raw_body)
    content = _as_dict(body.get("content"))
    json_content = content.get("application/json")
    if not isinstance(json_content, dict):
        return
    payload = _as_dict(json_content)
    schema = _as_dict(payload.get("schema"))
    ref = schema.get("$ref")
    if not isinstance(ref, str) or "example" in payload:
        return
    example = SCHEMA_EXAMPLES.get(ref.rsplit("/", 1)[-1])
    if example is None:
        return
    payload["example"] = example
    content["application/json"] = payload
    body["content"] = content
    operation["requestBody"] = body


def _set_header_required(operation: dict[str, Any], name: str, *, required: bool) -> None:
    parameters = operation.get("parameters")
    if not isinstance(parameters, list):
        return
    updated: list[object] = []
    for raw_item in parameters:
        if not isinstance(raw_item, dict):
            updated.append(raw_item)
            continue
        parameter = _as_dict(raw_item)
        if str(parameter.get("name")).lower() == name.lower():
            parameter["required"] = required
            if required:
                parameter["schema"] = {"type": "string"}
        updated.append(parameter)
    operation["parameters"] = updated


def _require_idempotency_key(operation: dict[str, Any]) -> None:
    parameters = operation.get("parameters")
    if not isinstance(parameters, list):
        return
    updated: list[object] = []
    for raw_item in parameters:
        if not isinstance(raw_item, dict):
            updated.append(raw_item)
            continue
        parameter = _as_dict(raw_item)
        if parameter.get("name") == "Idempotency-Key":
            parameter["required"] = True
            schema = _as_dict(parameter.get("schema"))
            if "anyOf" in schema:
                parameter["schema"] = {"type": "string", "minLength": 1, "maxLength": 128}
            else:
                schema.setdefault("minLength", 1)
                schema.setdefault("maxLength", 128)
                parameter["schema"] = schema
        updated.append(parameter)
    operation["parameters"] = updated


def _ensure_success_example(response: dict[str, Any]) -> None:
    content = _as_dict(response.get("content"))
    json_content = content.get("application/json")
    if not isinstance(json_content, dict):
        return
    payload = _as_dict(json_content)
    schema = _as_dict(payload.get("schema"))
    ref = schema.get("$ref")
    if isinstance(ref, str) and "example" not in payload:
        name = ref.rsplit("/", 1)[-1]
        example = SCHEMA_EXAMPLES.get(name)
        if example is not None:
            payload["example"] = example
            content["application/json"] = payload
            response["content"] = content


SCHEMA_EXAMPLES: dict[str, dict[str, object]] = {
    "LiveResponse": {"status": "ok"},
    "ReadyResponse": {"status": "ready", "components": {"database": "ok"}},
    "VersionResponse": {
        "version": "0.1.0",
        "commit": "abc1234",
        "build_time": "2026-08-31T00:00:00Z",
    },
    "CreateOrganizationRequest": {
        "name": "Demo México",
        "slug": "demo-mexico",
        "functional_currency": "MXN",
        "fiscal_year_start_month": 1,
    },
    "CreateAccountRequest": {
        "code": "6100",
        "name": "Servicios externos",
        "account_type": "expense",
        "parent_id": None,
    },
    "CreateImportRequest": {
        "import_type": "actual",
        "budget_version_id": None,
        "original_filename": "actuals-2026.xlsx",
        "size_bytes": 123456,
        "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "template_version": "1.0",
    },
    "ValidateImportRequest": {
        "mapping": {
            "period": "Month",
            "account_code": "Account",
            "department_code": "Department",
            "cost_center_code": "Cost Center",
            "amount": "Actual",
            "currency": "Currency",
        },
        "create_missing_dimensions": False,
    },
    "VarianceSummaryResponse": {
        "scope": {
            "fiscal_year": 2026,
            "period_from": "2026-01-01",
            "period_to": "2026-06-01",
            "budget_version_id": "00000000-0000-0000-0000-000000000001",
            "currency": "MXN",
        },
        "metrics": {
            "budget_amount": "1000000.0000",
            "actual_amount": "1080000.0000",
            "variance_amount": "80000.0000",
            "variance_percent": "0.080000",
            "variance_state": "defined",
            "favorability": "unknown",
        },
    },
    "CreateExportRequest": {
        "export_type": "variance_breakdown",
        "format": "csv",
        "filters": {},
        "group_by": "account",
    },
    "ScenarioRuleRequest": {
        "sequence": 1,
        "scope": {
            "period_from": "2026-07-01",
            "period_to": "2026-12-01",
            "account_ids": [],
            "department_ids": ["00000000-0000-0000-0000-000000000002"],
            "cost_center_ids": [],
        },
        "operation": "percentage_change",
        "value": "0.0500",
    },
    "CreateMessageRequest": {
        "content": "¿Qué cuentas explican el exceso de gasto?",
        "context": {
            "fiscal_year": 2026,
            "period_from": "2026-01-01",
            "period_to": "2026-06-01",
            "budget_version_id": "00000000-0000-0000-0000-000000000001",
            "department_ids": ["00000000-0000-0000-0000-000000000002"],
        },
    },
}


def _as_dict(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    typed = cast(dict[object, object], value)
    return {str(key): item for key, item in typed.items()}
