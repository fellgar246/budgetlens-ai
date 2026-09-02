from __future__ import annotations

from pathlib import Path
from typing import Literal, NotRequired, TypedDict

REPO_ROOT = Path(__file__).resolve().parents[3]

Priority = Literal["must", "should", "could"]
RequirementStatus = Literal["implemented", "deferred", "partial", "blocked"]
PlanStatus = Literal["complete", "implemented", "pending", "blocked"]
Severity = Literal["low", "medium", "high"]
MitigationStatus = Literal["verified", "partial", "unverified"]
RiskCategory = Literal[
    "quality",
    "security",
    "privacy",
    "cost_external",
    "reliability",
    "product",
    "operations",
]
ReleaseScope = Literal["local", "aws", "prod"]

PROTECTED_ACCEPTANCE_CATEGORIES: frozenset[str] = frozenset(
    {"security", "privacy", "cost_external"}
)
AGENT_ACCEPTANCE_VALUES: frozenset[str] = frozenset({"agent", "auto", "default"})


class FunctionalGroup(TypedDict):
    requirements: str
    ids: list[str]
    primary_specs: str
    plans: list[str]
    acceptance: list[str]


class FunctionalRequirement(TypedDict):
    id: str
    summary: str
    priority: Priority
    status: RequirementStatus
    primary_specs: list[str]
    plans: list[str]
    acceptance: list[str]
    evidence: list[str]
    backlog_id: NotRequired[str]
    deferred_reason: NotRequired[str]


class NonFunctionalRequirement(TypedDict):
    id: str
    summary: str
    status: RequirementStatus
    plans: list[str]
    evidence: list[str]


class AcceptanceCriterion(TypedDict):
    id: str
    summary: str
    evidence: list[str]
    kind: Literal["suite", "runbook", "both"]


class PlanRecord(TypedDict):
    id: str
    name: str
    status: PlanStatus
    requirements: list[str]
    acceptance: list[str]


class GateRecord(TypedDict):
    id: str
    name: str
    plans: list[str]
    owner: str
    moment: str
    local_simulation: str
    blocks: str
    deliverables: list[str]
    human_actions: list[str]
    blocks_release: list[ReleaseScope]


class RiskRecord(TypedDict):
    id: str
    summary: str
    likelihood: Severity
    impact: Severity
    mitigation: str
    owner: str
    trigger: str
    category: RiskCategory
    mitigation_status: MitigationStatus
    evidence: list[str]
    blocks_release: list[ReleaseScope]
    accepted_by: NotRequired[str | None]
    accepted_on: NotRequired[str | None]
    impact_changed_on: NotRequired[str | None]
    realized: NotRequired[bool]
    incident: NotRequired[str]
    regression_evidence: NotRequired[str]


class BacklogItem(TypedDict):
    id: str
    summary: str
    source: str
    priority: Priority


FUNCTIONAL_GROUPS: list[FunctionalGroup] = [
    {
        "requirements": "FR-ORG-001–005",
        "ids": [f"FR-ORG-{index:03d}" for index in range(1, 6)],
        "primary_specs": "Product/API/Security",
        "plans": ["01", "06"],
        "acceptance": ["AC-011", "AC-013", "AC-015"],
    },
    {
        "requirements": "FR-DIM-001–003",
        "ids": [f"FR-DIM-{index:03d}" for index in range(1, 4)],
        "primary_specs": "Domain/API",
        "plans": ["01", "04"],
        "acceptance": [],
    },
    {
        "requirements": "FR-BUD-001–004",
        "ids": [f"FR-BUD-{index:03d}" for index in range(1, 5)],
        "primary_specs": "Business rules/API",
        "plans": ["01", "04"],
        "acceptance": ["AC-002", "AC-005", "AC-006", "AC-007", "AC-008", "AC-009", "AC-010"],
    },
    {
        "requirements": "FR-IMP-001–010",
        "ids": [f"FR-IMP-{index:03d}" for index in range(1, 11)],
        "primary_specs": "Import/export contract",
        "plans": ["02", "04"],
        "acceptance": ["AC-002", "AC-003", "AC-004", "AC-014"],
    },
    {
        "requirements": "FR-ANA-001–009",
        "ids": [f"FR-ANA-{index:03d}" for index in range(1, 10)],
        "primary_specs": "Business rules/API/UX",
        "plans": ["03", "04"],
        "acceptance": ["AC-005", "AC-006", "AC-007", "AC-008", "AC-009", "AC-010"],
    },
    {
        "requirements": "FR-AI-001–009",
        "ids": [f"FR-AI-{index:03d}" for index in range(1, 10)],
        "primary_specs": "AI architecture/dataset",
        "plans": ["05", "06"],
        "acceptance": ["AC-017", "AC-018", "AC-019", "AC-020", "AC-021", "AC-022"],
    },
    {
        "requirements": "FR-AUD-001–003",
        "ids": [f"FR-AUD-{index:03d}" for index in range(1, 4)],
        "primary_specs": "Observability/audit",
        "plans": ["01", "02", "05", "07"],
        "acceptance": ["AC-011", "AC-016", "AC-023", "AC-024", "AC-025"],
    },
    {
        "requirements": "FR-OPS-001–004",
        "ids": [f"FR-OPS-{index:03d}" for index in range(1, 5)],
        "primary_specs": "Observability/infrastructure",
        "plans": ["00", "07", "08", "09", "10"],
        "acceptance": ["AC-023", "AC-024", "AC-025", "AC-026"],
    },
    {
        "requirements": "FR-UI-001–005",
        "ids": [f"FR-UI-{index:03d}" for index in range(1, 6)],
        "primary_specs": "UX/UI + UI Guidelines",
        "plans": ["04", "05", "06"],
        "acceptance": ["AC-013"],
    },
]

FUNCTIONAL_REQUIREMENTS: list[FunctionalRequirement] = [
    {
        "id": "FR-ORG-001",
        "summary": "Create an organization with name, slug, currency, and fiscal start month",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Product/API/Security"],
        "plans": ["01", "06"],
        "acceptance": ["AC-011", "AC-013", "AC-015"],
        "evidence": [
            "apps/api/src/budgetlens/presentation/routes/session.py",
            "apps/api/tests/integration/test_domain_api.py",
        ],
    },
    {
        "id": "FR-ORG-002",
        "summary": "List only organizations the user belongs to",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Product/API/Security"],
        "plans": ["01", "06"],
        "acceptance": ["AC-011"],
        "evidence": [
            "apps/api/src/budgetlens/presentation/routes/session.py",
            "apps/api/tests/integration/test_personas_and_tenancy.py",
        ],
    },
    {
        "id": "FR-ORG-003",
        "summary": "Switch the active organization without keeping the previous tenant cache",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Product/API/Security"],
        "plans": ["01", "06"],
        "acceptance": ["AC-013"],
        "evidence": [
            "apps/web/src/features/session/SessionProvider.tsx",
            "apps/api/tests/integration/test_personas_and_tenancy.py::test_switching_organization_does_not_leak_other_tenant",
        ],
    },
    {
        "id": "FR-ORG-004",
        "summary": "Manage members with viewer, analyst, and admin roles",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Product/API/Security"],
        "plans": ["01", "06"],
        "acceptance": ["AC-011"],
        "evidence": [
            "apps/api/src/budgetlens/presentation/routes/memberships.py",
            "apps/api/tests/integration/test_domain_api.py::test_admin_manages_members_and_viewer_cannot",
        ],
    },
    {
        "id": "FR-ORG-005",
        "summary": "Archive an organization without physical delete from the UI",
        "priority": "should",
        "status": "deferred",
        "primary_specs": ["Product/API/Security"],
        "plans": ["01", "06"],
        "acceptance": [],
        "evidence": [],
        "backlog_id": "BL-1101",
        "deferred_reason": "Settings can patch name and fiscal month; archive is not in the UI.",
    },
    {
        "id": "FR-DIM-001",
        "summary": "Manage accounts with unique code, name, and type",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Domain/API"],
        "plans": ["01", "04"],
        "acceptance": [],
        "evidence": [
            "apps/api/src/budgetlens/presentation/routes/dimensions.py",
            "apps/api/tests/integration/test_domain_api.py",
        ],
    },
    {
        "id": "FR-DIM-002",
        "summary": "Manage departments and cost centers",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Domain/API"],
        "plans": ["01", "04"],
        "acceptance": [],
        "evidence": [
            "apps/api/src/budgetlens/presentation/routes/dimensions.py",
            "apps/web/src/features/catalog/CatalogPage.tsx",
        ],
    },
    {
        "id": "FR-DIM-003",
        "summary": "Keep an explicit UNASSIGNED dimension",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Domain/API"],
        "plans": ["01", "04"],
        "acceptance": [],
        "evidence": [
            "apps/api/tests/unit/domain/test_permissions_and_rules.py::test_empty_cost_center_resolves_to_unassigned",
        ],
    },
    {
        "id": "FR-BUD-001",
        "summary": "Create budget versions per fiscal year",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Business rules/API"],
        "plans": ["01", "04"],
        "acceptance": ["AC-002"],
        "evidence": [
            "apps/api/src/budgetlens/presentation/routes/budget_versions.py",
            "apps/api/tests/integration/test_domain_api.py",
        ],
    },
    {
        "id": "FR-BUD-002",
        "summary": "Publish a version and make its entries immutable",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Business rules/API"],
        "plans": ["01", "04"],
        "acceptance": ["AC-002"],
        "evidence": [
            "apps/api/tests/unit/domain/test_budget_version.py::test_publish_makes_version_immutable",
        ],
    },
    {
        "id": "FR-BUD-003",
        "summary": "Mark one published version as active",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Business rules/API"],
        "plans": ["01", "04"],
        "acceptance": [],
        "evidence": [
            "apps/api/tests/integration/test_domain_api.py::test_only_one_active_version_per_fiscal_year",
        ],
    },
    {
        "id": "FR-BUD-004",
        "summary": "Archive versions while keeping historical analysis",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Business rules/API"],
        "plans": ["01", "04"],
        "acceptance": [],
        "evidence": [
            "apps/api/tests/unit/domain/test_budget_version.py::test_archive_keeps_trace_and_clears_active",
        ],
    },
    {
        "id": "FR-IMP-001",
        "summary": "Accept UTF-8 CSV and XLSX without macros",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Import/export contract"],
        "plans": ["02", "04"],
        "acceptance": ["AC-002"],
        "evidence": [
            "apps/api/tests/integration/test_import_and_analytics.py::test_valid_csv_and_xlsx_import_same_totals",
        ],
    },
    {
        "id": "FR-IMP-002",
        "summary": "Validate size, extension, MIME, and headers",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Import/export contract"],
        "plans": ["02", "04"],
        "acceptance": ["AC-003", "AC-014"],
        "evidence": [
            "apps/api/src/budgetlens/domain/importing.py",
            "apps/api/tests/unit/domain/test_importing.py",
        ],
    },
    {
        "id": "FR-IMP-003",
        "summary": "Map columns to canonical fields",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Import/export contract"],
        "plans": ["02", "04"],
        "acceptance": ["AC-002"],
        "evidence": [
            "apps/api/tests/unit/domain/test_importing.py::test_mapping_requires_canonical_fields",
        ],
    },
    {
        "id": "FR-IMP-004",
        "summary": "Show preview, totals, warnings, and errors before commit",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Import/export contract"],
        "plans": ["02", "04"],
        "acceptance": ["AC-002", "AC-003"],
        "evidence": [
            "apps/api/src/budgetlens/application/imports.py",
            "apps/web/src/features/imports/ImportsPage.tsx",
        ],
    },
    {
        "id": "FR-IMP-005",
        "summary": "Download errors with row number and code",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Import/export contract"],
        "plans": ["02", "04"],
        "acceptance": ["AC-003"],
        "evidence": [
            "apps/api/src/budgetlens/presentation/routes/imports.py",
            "apps/api/tests/integration/test_import_and_analytics.py::test_invalid_row_blocks_commit_and_leaves_no_entries",
        ],
    },
    {
        "id": "FR-IMP-006",
        "summary": "Apply a file in one atomic transaction",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Import/export contract"],
        "plans": ["02", "04"],
        "acceptance": ["AC-003"],
        "evidence": [
            "apps/api/tests/integration/test_import_and_analytics.py::test_invalid_row_blocks_commit_and_leaves_no_entries",
        ],
    },
    {
        "id": "FR-IMP-007",
        "summary": "Prevent duplicates with an idempotent fingerprint",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Import/export contract"],
        "plans": ["02", "04"],
        "acceptance": ["AC-004"],
        "evidence": [
            "apps/api/tests/integration/test_import_and_analytics.py::test_commit_retry_is_idempotent_and_analytics_match",
        ],
    },
    {
        "id": "FR-IMP-008",
        "summary": "Keep the original file and job metadata",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Import/export contract"],
        "plans": ["02", "04"],
        "acceptance": ["AC-002"],
        "evidence": [
            "apps/api/src/budgetlens/application/imports.py",
            "apps/api/tests/unit/test_watchdog_and_retention.py",
        ],
    },
    {
        "id": "FR-IMP-009",
        "summary": "Cancel a job that has not been applied",
        "priority": "should",
        "status": "implemented",
        "primary_specs": ["Import/export contract"],
        "plans": ["02", "04"],
        "acceptance": [],
        "evidence": [
            "apps/api/src/budgetlens/application/imports.py",
            "apps/web/src/features/imports/ImportsPage.tsx",
        ],
    },
    {
        "id": "FR-IMP-010",
        "summary": "Explicitly replace an existing data range",
        "priority": "should",
        "status": "deferred",
        "primary_specs": ["Import/export contract"],
        "plans": ["02", "04"],
        "acceptance": [],
        "evidence": [],
        "backlog_id": "BL-1102",
        "deferred_reason": "Imports apply a new batch; explicit range replace is not exposed.",
    },
    {
        "id": "FR-ANA-001",
        "summary": "Calculate budget, actual, variance amount, and variance percent",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Business rules/API/UX"],
        "plans": ["03", "04"],
        "acceptance": ["AC-005"],
        "evidence": [
            "apps/api/tests/unit/domain/test_variance.py",
            "apps/api/src/budgetlens/application/analytics.py",
        ],
    },
    {
        "id": "FR-ANA-002",
        "summary": "Classify favorable, unfavorable, neutral, or unknown",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Business rules/API/UX"],
        "plans": ["03", "04"],
        "acceptance": ["AC-006", "AC-007"],
        "evidence": [
            "apps/api/tests/unit/domain/test_variance.py::test_expense_over_budget_is_unfavorable",
            "apps/api/tests/unit/domain/test_variance.py::test_revenue_over_budget_is_favorable",
        ],
    },
    {
        "id": "FR-ANA-003",
        "summary": "Filter by period, version, account, department, and cost center",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Business rules/API/UX"],
        "plans": ["03", "04"],
        "acceptance": ["AC-008"],
        "evidence": [
            "apps/api/src/budgetlens/application/analytics.py",
            "apps/web/src/features/analysis/FilterBar.tsx",
        ],
    },
    {
        "id": "FR-ANA-004",
        "summary": "Group by month and one requested dimension",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Business rules/API/UX"],
        "plans": ["03", "04"],
        "acceptance": ["AC-008"],
        "evidence": ["apps/api/src/budgetlens/application/analytics.py"],
    },
    {
        "id": "FR-ANA-005",
        "summary": "Show the main contributors to a variance",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Business rules/API/UX"],
        "plans": ["03", "04"],
        "acceptance": ["AC-008"],
        "evidence": [
            "apps/api/src/budgetlens/application/analytics.py",
            "apps/web/src/features/variances/VariancesPage.tsx",
        ],
    },
    {
        "id": "FR-ANA-006",
        "summary": "Drill down while keeping context",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Business rules/API/UX"],
        "plans": ["03", "04"],
        "acceptance": ["AC-008"],
        "evidence": [
            "apps/web/tests/analysis-filters.test.ts",
            "apps/web/src/lib/analysis-filters.ts",
        ],
    },
    {
        "id": "FR-ANA-007",
        "summary": "Export the filtered result as CSV",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Business rules/API/UX"],
        "plans": ["03", "04"],
        "acceptance": ["AC-009"],
        "evidence": [
            "apps/api/tests/integration/test_import_and_analytics.py::test_export_download_is_authorized_and_expires",
        ],
    },
    {
        "id": "FR-ANA-008",
        "summary": "Create deterministic, non-destructive scenarios",
        "priority": "should",
        "status": "implemented",
        "primary_specs": ["Business rules/API/UX"],
        "plans": ["03", "04"],
        "acceptance": ["AC-010"],
        "evidence": [
            "apps/api/tests/integration/test_import_and_analytics.py::test_scenario_preview_does_not_mutate_entries",
        ],
    },
    {
        "id": "FR-ANA-009",
        "summary": "Compare baseline against a scenario",
        "priority": "should",
        "status": "implemented",
        "primary_specs": ["Business rules/API/UX"],
        "plans": ["03", "04"],
        "acceptance": ["AC-010"],
        "evidence": [
            "apps/api/src/budgetlens/application/scenarios.py",
            "apps/web/src/features/scenarios/ScenariosPage.tsx",
        ],
    },
    {
        "id": "FR-AI-001",
        "summary": "Create conversations inside an organization",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["AI architecture/dataset"],
        "plans": ["05", "06"],
        "acceptance": ["AC-017"],
        "evidence": ["apps/api/src/budgetlens/presentation/routes/conversations.py"],
    },
    {
        "id": "FR-AI-002",
        "summary": "Answer figures only through registered tools",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["AI architecture/dataset"],
        "plans": ["05", "06"],
        "acceptance": ["AC-017"],
        "evidence": [
            "apps/api/src/budgetlens/application/ai.py",
            "apps/api/src/budgetlens/domain/tools.py",
            "apps/api/tests/integration/test_import_and_analytics.py::test_copilot_uses_tools_and_rejects_mutations",
        ],
    },
    {
        "id": "FR-AI-003",
        "summary": "Apply view context filters as structured tool arguments",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["AI architecture/dataset"],
        "plans": ["05", "06"],
        "acceptance": ["AC-017"],
        "evidence": ["apps/api/src/budgetlens/application/ai.py"],
    },
    {
        "id": "FR-AI-004",
        "summary": "Show evidence, tool, period, version, and currency",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["AI architecture/dataset"],
        "plans": ["05", "06"],
        "acceptance": ["AC-017"],
        "evidence": [
            "apps/web/src/features/copilot/CopilotPage.tsx",
            "apps/api/tests/unit/test_ai_eval.py",
        ],
    },
    {
        "id": "FR-AI-005",
        "summary": "Reject mutations and out-of-domain requests",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["AI architecture/dataset"],
        "plans": ["05", "06"],
        "acceptance": ["AC-019"],
        "evidence": [
            "apps/api/tests/integration/test_import_and_analytics.py::test_copilot_uses_tools_and_rejects_mutations",
        ],
    },
    {
        "id": "FR-AI-006",
        "summary": "Limit turns, tools, rows, and time per request",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["AI architecture/dataset"],
        "plans": ["05", "06"],
        "acceptance": ["AC-022"],
        "evidence": [
            "apps/api/src/budgetlens/application/ai.py",
            "apps/api/src/budgetlens/application/rate_limit.py",
            "apps/api/tests/unit/test_ai_concurrency.py",
        ],
    },
    {
        "id": "FR-AI-007",
        "summary": "Record usage and latency metadata without secrets",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["AI architecture/dataset"],
        "plans": ["05", "06"],
        "acceptance": ["AC-016"],
        "evidence": [
            "apps/api/src/budgetlens/application/ai.py",
            "apps/api/tests/unit/test_logging_sanitization.py",
        ],
    },
    {
        "id": "FR-AI-008",
        "summary": "Run with a stub provider for local tests",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["AI architecture/dataset"],
        "plans": ["05", "06"],
        "acceptance": ["AC-017"],
        "evidence": ["apps/api/tests/unit/test_ai_eval.py"],
    },
    {
        "id": "FR-AI-009",
        "summary": "Run the evaluation dataset against stub and Bedrock",
        "priority": "must",
        "status": "partial",
        "primary_specs": ["AI architecture/dataset"],
        "plans": ["05", "06"],
        "acceptance": ["AC-017", "AC-018", "AC-019", "AC-020", "AC-021", "AC-022"],
        "evidence": [
            "apps/api/src/budgetlens/application/ai_eval.py",
            "apps/api/src/budgetlens/application/ai_eval_dataset.py",
            "apps/api/tests/unit/test_ai_eval.py",
        ],
    },
    {
        "id": "FR-AUD-001",
        "summary": "Audit login, membership changes, imports, publishes, and exports",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Observability/audit"],
        "plans": ["01", "02", "05", "07"],
        "acceptance": ["AC-011", "AC-016"],
        "evidence": [
            "apps/api/src/budgetlens/application/audit.py",
            "apps/api/src/budgetlens/domain/audit.py",
            "apps/api/tests/integration/test_domain_api.py::test_critical_actions_audit_success_and_denied",
        ],
    },
    {
        "id": "FR-AUD-002",
        "summary": "Audit AI tools and argument/result hashes",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Observability/audit"],
        "plans": ["01", "02", "05", "07"],
        "acceptance": ["AC-016"],
        "evidence": ["apps/api/src/budgetlens/application/ai.py"],
    },
    {
        "id": "FR-AUD-003",
        "summary": "Query audit by organization, actor, action, and date",
        "priority": "should",
        "status": "implemented",
        "primary_specs": ["Observability/audit"],
        "plans": ["01", "02", "05", "07"],
        "acceptance": [],
        "evidence": ["apps/api/src/budgetlens/presentation/routes/audit.py"],
    },
    {
        "id": "FR-OPS-001",
        "summary": "Expose process health and dependency readiness",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Observability/infrastructure"],
        "plans": ["00", "07", "08", "09", "10"],
        "acceptance": ["AC-023"],
        "evidence": [
            "apps/api/tests/unit/test_health_live.py",
            "apps/api/tests/unit/test_health_ready.py",
        ],
    },
    {
        "id": "FR-OPS-002",
        "summary": "Emit correlated JSON logs",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Observability/infrastructure"],
        "plans": ["00", "07", "08", "09", "10"],
        "acceptance": ["AC-016"],
        "evidence": [
            "apps/api/src/budgetlens/logging.py",
            "apps/api/tests/unit/test_trace_id.py",
        ],
    },
    {
        "id": "FR-OPS-003",
        "summary": "Publish API, job, database, and AI metrics",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Observability/infrastructure"],
        "plans": ["00", "07", "08", "09", "10"],
        "acceptance": ["AC-023"],
        "evidence": [
            "apps/api/src/budgetlens/observability.py",
            "apps/api/src/budgetlens/presentation/routes/ops.py",
        ],
    },
    {
        "id": "FR-OPS-004",
        "summary": "Document rollback and restore",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["Observability/infrastructure"],
        "plans": ["00", "07", "08", "09", "10"],
        "acceptance": ["AC-025", "AC-026"],
        "evidence": [
            "docs/OPERATIONS.md",
            "docs/CICD.md",
            "docs/GATES.md",
            "docs/DEPLOYMENT.md",
            "scripts/rollback-release.sh",
            "scripts/teardown-environment.sh",
            "scripts/restore-test.sh",
            "scripts/deploy_preflight.py",
            "scripts/record_cost_estimate.py",
            "scripts/record_gate.py",
        ],
    },
    {
        "id": "FR-UI-001",
        "summary": "Show navigation, active organization, and profile",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["UX/UI + UI Guidelines"],
        "plans": ["04", "05", "06"],
        "acceptance": ["AC-013"],
        "evidence": [
            "apps/web/src/components/layout/AppShell.tsx",
            "apps/web/src/components/layout/AppHeader.tsx",
        ],
    },
    {
        "id": "FR-UI-002",
        "summary": "Represent loading, empty, error, and success on every data view",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["UX/UI + UI Guidelines"],
        "plans": ["04", "05", "06"],
        "acceptance": [],
        "evidence": [
            "apps/web/src/features/dashboard/DashboardPage.tsx",
            "apps/web/tests/dashboard-page.test.tsx",
        ],
    },
    {
        "id": "FR-UI-003",
        "summary": "Allow keyboard use and a visible focus on critical flows",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["UX/UI + UI Guidelines"],
        "plans": ["04", "05", "06"],
        "acceptance": [],
        "evidence": [
            "apps/web/src/app/globals.css",
            "apps/web/src/components/layout/AppSidebar.tsx",
        ],
    },
    {
        "id": "FR-UI-004",
        "summary": "Adapt to desktop and tablet; mobile keeps basic reading",
        "priority": "should",
        "status": "implemented",
        "primary_specs": ["UX/UI + UI Guidelines"],
        "plans": ["04", "05", "06"],
        "acceptance": [],
        "evidence": [
            "apps/web/src/components/layout/AppShell.tsx",
            "apps/web/src/components/layout/AppSidebar.tsx",
        ],
    },
    {
        "id": "FR-UI-005",
        "summary": "Format money, percent, and dates by locale without changing values",
        "priority": "must",
        "status": "implemented",
        "primary_specs": ["UX/UI + UI Guidelines"],
        "plans": ["04", "05", "06"],
        "acceptance": ["AC-005"],
        "evidence": [
            "apps/web/src/lib/format.ts",
            "apps/web/tests/format-and-variance.test.tsx",
        ],
    },
]

NON_FUNCTIONAL_REQUIREMENTS: list[NonFunctionalRequirement] = [
    {
        "id": "NFR-PERF-001",
        "summary": "Read API p95 under 500 ms at 250k entries per tenant, excluding AI",
        "status": "partial",
        "plans": ["02", "03", "04", "05", "07"],
        "evidence": [
            "scripts/load_test.py",
            "scripts/generate_large_dataset.py",
            "docs/OPERATIONS.md",
        ],
    },
    {
        "id": "NFR-PERF-002",
        "summary": "Initial dashboard usable under 2.5 s p75 on the reference connection",
        "status": "partial",
        "plans": ["02", "03", "04", "05", "07"],
        "evidence": ["apps/web/src/features/dashboard/DashboardPage.tsx"],
    },
    {
        "id": "NFR-PERF-003",
        "summary": "Preview a 25 MiB file in under 60 s",
        "status": "implemented",
        "plans": ["02", "03", "04", "05", "07"],
        "evidence": ["apps/api/tests/unit/test_large_preview.py"],
    },
    {
        "id": "NFR-PERF-004",
        "summary": "Copilot response under 20 s p95, with progress after 1 s",
        "status": "partial",
        "plans": ["02", "03", "04", "05", "07"],
        "evidence": ["apps/web/src/features/copilot/CopilotPage.tsx"],
    },
    {
        "id": "NFR-PERF-005",
        "summary": "No endpoint returns more than 500 rows without pagination",
        "status": "implemented",
        "plans": ["02", "03", "04", "05", "07"],
        "evidence": ["apps/api/tests/unit/test_pagination_contract.py"],
    },
    {
        "id": "NFR-REL-001",
        "summary": "99.5% monthly availability for prod; no SLA for dev",
        "status": "partial",
        "plans": ["02", "07", "09", "10"],
        "evidence": [
            "docs/OPERATIONS.md",
            "docs/DEPLOYMENT.md",
            "apps/api/tests/unit/test_cost_and_operations.py",
        ],
    },
    {
        "id": "NFR-REL-002",
        "summary": "RPO 24 hours and RTO 4 hours for release 1.0",
        "status": "partial",
        "plans": ["02", "07", "09", "10"],
        "evidence": [
            "docs/OPERATIONS.md",
            "docs/DEPLOYMENT.md",
            "scripts/snapshot-db.sh",
            "scripts/restore-test.sh",
        ],
    },
    {
        "id": "NFR-REL-003",
        "summary": "Imports and publishes are atomic",
        "status": "implemented",
        "plans": ["02", "07", "09", "10"],
        "evidence": [
            "apps/api/tests/integration/test_import_and_analytics.py::test_invalid_row_blocks_commit_and_leaves_no_entries",
            "apps/api/tests/integration/test_risk_invariants.py::test_injected_commit_failure_leaves_no_entries",
        ],
    },
    {
        "id": "NFR-REL-004",
        "summary": "Recoverable jobs do not stay in processing; watchdog marks timeout",
        "status": "implemented",
        "plans": ["02", "07", "09", "10"],
        "evidence": ["apps/api/tests/unit/test_watchdog_and_retention.py"],
    },
    {
        "id": "NFR-REL-005",
        "summary": "Deployments keep at least one identifiable previous image for rollback",
        "status": "implemented",
        "plans": ["02", "07", "09", "10"],
        "evidence": [
            "Makefile",
            "docs/OPERATIONS.md",
            "scripts/rollback-release.sh",
            ".github/workflows/deploy-dev.yml",
        ],
    },
    {
        "id": "NFR-SEC-001",
        "summary": "TLS in transit and managed encryption for AWS storage",
        "status": "partial",
        "plans": ["02", "05", "06", "07", "08", "09", "10"],
        "evidence": [
            "docs/OPERATIONS.md",
            "infrastructure/terraform/modules/storage/main.tf",
            "infrastructure/terraform/modules/database/main.tf",
            "apps/api/tests/unit/test_terraform_architecture.py",
        ],
    },
    {
        "id": "NFR-SEC-002",
        "summary": "AWS credentials through roles/OIDC, not permanent CI access keys",
        "status": "implemented",
        "plans": ["02", "05", "06", "07", "08", "09", "10"],
        "evidence": [
            "docs/OPERATIONS.md",
            "docs/CICD.md",
            "infrastructure/terraform/modules/github_oidc/main.tf",
            ".github/workflows/deploy-prod.yml",
            "apps/api/tests/unit/test_architecture_decisions.py",
            "apps/api/tests/unit/test_cicd_release.py",
        ],
    },
    {
        "id": "NFR-SEC-003",
        "summary": "Deny-by-default authorization on every business operation",
        "status": "implemented",
        "plans": ["02", "05", "06", "07", "08", "09", "10"],
        "evidence": [
            "apps/api/tests/unit/domain/test_permissions_and_rules.py",
            "apps/api/tests/integration/test_personas_and_tenancy.py",
        ],
    },
    {
        "id": "NFR-SEC-004",
        "summary": "Cross-tenant isolation tests for endpoints, exports, files, and conversations",
        "status": "implemented",
        "plans": ["02", "05", "06", "07", "08", "09", "10"],
        "evidence": [
            "apps/api/tests/integration/test_domain_api.py::test_alpha_cannot_read_or_mutate_beta",
            "apps/api/tests/integration/test_import_and_analytics.py::test_viewer_cannot_import_and_alpha_cannot_read_beta_job",
            "apps/api/tests/integration/test_rls_and_idor.py::test_cross_tenant_idor_covers_jobs_scenarios_conversations_and_exports",
            "apps/api/tests/integration/test_rls_and_idor.py::test_runtime_role_has_no_bypass_and_rls_requires_org_guc",
        ],
    },
    {
        "id": "NFR-SEC-005",
        "summary": "Dependencies and images scanned; confirmed critical findings block release",
        "status": "implemented",
        "plans": ["02", "05", "06", "07", "08", "09", "10"],
        "evidence": ["scripts/scan.sh", "docs/OPERATIONS.md", ".github/workflows/build.yml"],
    },
    {
        "id": "NFR-SEC-006",
        "summary": "Secrets never appear in logs, errors, Terraform plans, or web bundles",
        "status": "implemented",
        "plans": ["02", "05", "06", "07", "08", "09", "10"],
        "evidence": ["apps/api/tests/unit/test_logging_sanitization.py"],
    },
    {
        "id": "NFR-SEC-007",
        "summary": "Uploads are not executed; XLSM, formulas, and encrypted files are rejected",
        "status": "implemented",
        "plans": ["02", "05", "06", "07", "08", "09", "10"],
        "evidence": [
            "apps/api/tests/integration/test_import_and_analytics.py::test_formula_xlsx_is_rejected",
            "apps/api/tests/unit/test_upload_boundaries.py::test_macro_enabled_workbook_is_rejected",
        ],
    },
    {
        "id": "NFR-PRI-001",
        "summary": "Demo data is synthetic; no real business data is versioned",
        "status": "implemented",
        "plans": ["02", "05", "06", "07", "08", "09", "10"],
        "evidence": ["apps/api/src/budgetlens/seed.py", ".gitignore"],
    },
    {
        "id": "NFR-PRI-002",
        "summary": "Logs do not contain full financial rows or full prompts by default",
        "status": "implemented",
        "plans": ["02", "05", "06", "07", "08", "09", "10"],
        "evidence": ["apps/api/tests/unit/test_logging_sanitization.py"],
    },
    {
        "id": "NFR-PRI-003",
        "summary": "Original files have configurable retention; initial 90 days in dev",
        "status": "implemented",
        "plans": ["02", "05", "06", "07", "08", "09", "10"],
        "evidence": ["apps/api/tests/unit/test_watchdog_and_retention.py", "docs/OPERATIONS.md"],
    },
    {
        "id": "NFR-PRI-004",
        "summary": "Conversations can be logically deleted; audit keeps metadata",
        "status": "implemented",
        "plans": ["02", "05", "06", "07", "08", "09", "10"],
        "evidence": ["apps/api/src/budgetlens/domain/conversation.py", "docs/OPERATIONS.md"],
    },
    {
        "id": "NFR-PRI-005",
        "summary": "Exports use temporary URLs and authorization on create and download",
        "status": "implemented",
        "plans": ["02", "05", "06", "07", "08", "09", "10"],
        "evidence": [
            "apps/api/tests/integration/test_import_and_analytics.py::test_export_download_is_authorized_and_expires",
        ],
    },
    {
        "id": "NFR-UX-001",
        "summary": "Critical flows meet WCAG 2.2 AA for contrast, keyboard, labels, and focus",
        "status": "partial",
        "plans": ["04", "07"],
        "evidence": [
            "apps/web/src/app/globals.css",
            "apps/web/src/components/layout/AppSidebar.tsx",
            "apps/web/e2e/journeys.spec.ts",
        ],
    },
    {
        "id": "NFR-UX-002",
        "summary": "Favorability is not communicated by color alone",
        "status": "implemented",
        "plans": ["04", "07"],
        "evidence": ["apps/web/tests/format-and-variance.test.tsx"],
    },
    {
        "id": "NFR-UX-003",
        "summary": "Errors show a corrective action and keep safe entered data",
        "status": "implemented",
        "plans": ["04", "07"],
        "evidence": [
            "apps/web/src/components/ui/ErrorBanner.tsx",
            "apps/web/tests/format-and-variance.test.tsx",
        ],
    },
    {
        "id": "NFR-UX-004",
        "summary": "Amounts always show currency; percent without budget is N/A, not 0%",
        "status": "implemented",
        "plans": ["04", "07"],
        "evidence": ["apps/web/src/lib/format.ts", "apps/web/tests/format-and-variance.test.tsx"],
    },
    {
        "id": "NFR-MNT-001",
        "summary": "Coverage at least 85% on financial-core and 75% backend overall",
        "status": "implemented",
        "plans": ["00", "01", "02", "03", "04", "05", "06", "07", "08", "09"],
        "evidence": ["Makefile", ".github/workflows/ci.yml"],
    },
    {
        "id": "NFR-MNT-002",
        "summary": "Strict type checking in TypeScript and Python",
        "status": "implemented",
        "plans": ["00", "01", "02", "03", "04", "05", "06", "07", "08", "09"],
        "evidence": ["apps/api/pyproject.toml", "apps/web/package.json"],
    },
    {
        "id": "NFR-MNT-003",
        "summary": "Forward-only migrations tested from an empty database",
        "status": "implemented",
        "plans": ["00", "01", "02", "03", "04", "05", "06", "07", "08", "09"],
        "evidence": ["apps/api/tests/integration/test_migrations.py"],
    },
    {
        "id": "NFR-MNT-004",
        "summary": "OpenAPI generated by the backend and checked against the client",
        "status": "implemented",
        "plans": ["00", "01", "02", "03", "04", "05", "06", "07", "08", "09"],
        "evidence": [
            "apps/api/tests/unit/test_openapi.py",
            "apps/api/src/budgetlens/presentation/openapi.py",
            "packages/api-client/openapi.json",
            "packages/api-client/src/index.ts",
        ],
    },
    {
        "id": "NFR-MNT-005",
        "summary": "Ports keep AWS SDKs out of domain and use cases",
        "status": "implemented",
        "plans": ["00", "01", "02", "03", "04", "05", "06", "07", "08", "09"],
        "evidence": [
            "apps/api/tests/unit/test_architecture_ports.py",
            "apps/api/tests/unit/test_repository_standards.py",
        ],
    },
    {
        "id": "NFR-MNT-006",
        "summary": "Every irreversible or costly decision has a recorded ADR",
        "status": "implemented",
        "plans": ["00", "01", "02", "03", "04", "05", "06", "07", "08", "09"],
        "evidence": [
            "docs/DECISIONS.md",
            "apps/api/tests/unit/test_decisions.py",
            "apps/api/tests/unit/test_architecture_decisions.py",
        ],
    },
    {
        "id": "NFR-OBS-001",
        "summary": "Every request has a trace_id in logs, jobs, and the response",
        "status": "implemented",
        "plans": ["00", "05", "07", "08", "10"],
        "evidence": ["apps/api/tests/unit/test_trace_id.py"],
    },
    {
        "id": "NFR-OBS-002",
        "summary": "Metrics include latency, errors, DB pool, jobs, AI use, and optional cost",
        "status": "implemented",
        "plans": ["00", "05", "07", "08", "10"],
        "evidence": [
            "apps/api/src/budgetlens/observability.py",
            "apps/api/tests/unit/test_observability.py",
        ],
    },
    {
        "id": "NFR-OBS-003",
        "summary": "Alarms distinguish application, dependency, and infrastructure failure",
        "status": "implemented",
        "plans": ["00", "05", "07", "08", "10"],
        "evidence": [
            "apps/api/tests/unit/test_rate_limit_and_headers.py",
            "docs/OPERATIONS.md",
            "infrastructure/terraform/modules/observability/main.tf",
        ],
    },
    {
        "id": "NFR-OBS-004",
        "summary": "Operational dashboards do not expose financial amounts",
        "status": "implemented",
        "plans": ["00", "05", "07", "08", "10"],
        "evidence": [
            "apps/api/tests/integration/test_personas_and_tenancy.py::test_ops_metrics_are_operator_only_and_non_financial",
        ],
    },
]

ACCEPTANCE_CRITERIA: list[AcceptanceCriterion] = [
    {
        "id": "AC-001",
        "summary": "Clean clone bootstrap starts web, API, and PostgreSQL",
        "kind": "both",
        "evidence": [
            "README.md",
            "scripts/bootstrap.sh",
            "scripts/acceptance-local-stack.sh",
            "apps/api/tests/unit/test_local_environment.py",
            "apps/api/tests/integration/acceptance/test_operations.py::test_migrated_stack_is_ready_and_at_head",
            "apps/web/tests/health-card.test.tsx",
            "apps/web/e2e/acceptance.spec.ts",
        ],
    },
    {
        "id": "AC-002",
        "summary": "Valid import applies once and dashboard totals match",
        "kind": "suite",
        "evidence": [
            "apps/api/tests/integration/acceptance/test_product.py::test_valid_import_applies_once_and_dashboard_matches",
        ],
    },
    {
        "id": "AC-003",
        "summary": "Invalid row blocks commit and leaves no entries",
        "kind": "suite",
        "evidence": [
            "apps/api/tests/integration/acceptance/test_product.py::test_invalid_row_blocks_commit_and_leaves_no_entries",
        ],
    },
    {
        "id": "AC-004",
        "summary": "Retry with the same key does not change row counts",
        "kind": "suite",
        "evidence": [
            "apps/api/tests/integration/acceptance/test_product.py::test_commit_retry_keeps_the_same_row_count",
            "apps/api/tests/integration/test_risk_invariants.py::test_concurrent_commit_does_not_duplicate_rows",
        ],
    },
    {
        "id": "AC-005",
        "summary": "Zero budget yields amount, null percent, unbounded, and N/A",
        "kind": "suite",
        "evidence": [
            "apps/api/tests/integration/acceptance/test_product.py::test_zero_budget_is_unbounded_with_null_percent",
            "apps/api/tests/unit/acceptance/test_rules_and_startup.py::test_zero_budget_nonzero_actual_is_unbounded",
            "apps/web/tests/acceptance-display.test.tsx",
        ],
    },
    {
        "id": "AC-006",
        "summary": "Expense over budget is unfavorable",
        "kind": "suite",
        "evidence": [
            "apps/api/tests/integration/acceptance/test_product.py::test_expense_over_budget_is_unfavorable",
            "apps/api/tests/unit/acceptance/test_rules_and_startup.py::test_expense_over_budget_is_unfavorable",
        ],
    },
    {
        "id": "AC-007",
        "summary": "Revenue over budget is favorable",
        "kind": "suite",
        "evidence": [
            "apps/api/tests/integration/acceptance/test_product.py::test_revenue_over_budget_is_favorable",
            "apps/api/tests/unit/acceptance/test_rules_and_startup.py::test_revenue_over_budget_is_favorable",
        ],
    },
    {
        "id": "AC-008",
        "summary": "Drill-down parts sum to the filtered total",
        "kind": "suite",
        "evidence": [
            "apps/api/tests/integration/acceptance/test_product.py::test_department_breakdown_sums_to_filtered_total",
            "apps/web/tests/acceptance-display.test.tsx",
            "apps/web/e2e/acceptance.spec.ts",
        ],
    },
    {
        "id": "AC-009",
        "summary": "Export CSV matches the filtered scope and totals",
        "kind": "suite",
        "evidence": [
            "apps/api/tests/integration/acceptance/test_product.py::test_export_csv_matches_scope_currency_version_and_totals",
        ],
    },
    {
        "id": "AC-010",
        "summary": "Scenario preview does not mutate budget or actuals",
        "kind": "suite",
        "evidence": [
            "apps/api/tests/integration/acceptance/test_product.py::test_scenario_preview_matches_saved_and_leaves_source_unchanged",
        ],
    },
    {
        "id": "AC-011",
        "summary": "Cross-tenant read returns 403/404 and audits denial",
        "kind": "suite",
        "evidence": [
            "apps/api/tests/integration/acceptance/test_security.py::test_cross_tenant_read_is_denied_without_metadata",
        ],
    },
    {
        "id": "AC-012",
        "summary": "Cross-tenant mutation does not change the other tenant",
        "kind": "suite",
        "evidence": [
            "apps/api/tests/integration/acceptance/test_security.py::test_cross_tenant_mutations_leave_beta_unchanged",
        ],
    },
    {
        "id": "AC-013",
        "summary": "Switching organization drops the previous tenant cache",
        "kind": "suite",
        "evidence": [
            "apps/api/tests/integration/acceptance/test_security.py::test_switching_organization_uses_the_new_membership",
            "apps/web/e2e/acceptance.spec.ts",
        ],
    },
    {
        "id": "AC-014",
        "summary": "XLSX formulas are rejected and never evaluated",
        "kind": "suite",
        "evidence": [
            "apps/api/tests/integration/acceptance/test_security.py::test_formula_workbook_is_rejected_and_not_applied",
        ],
    },
    {
        "id": "AC-015",
        "summary": "AUTH_MODE=dev fails closed unless APP_ENV is local or test",
        "kind": "suite",
        "evidence": [
            "apps/api/tests/unit/acceptance/test_rules_and_startup.py::test_create_app_rejects_dev_auth_in_prod_before_serving",
            "apps/api/tests/unit/test_dev_auth.py::test_create_app_rejects_dev_auth_in_prod",
            "apps/api/tests/unit/test_config.py::test_prod_rejects_dev_auth",
        ],
    },
    {
        "id": "AC-016",
        "summary": "Logs and error bodies do not contain secrets",
        "kind": "suite",
        "evidence": [
            "apps/api/tests/integration/acceptance/test_security.py::test_error_responses_and_logs_omit_secrets",
            "apps/api/tests/unit/test_logging_sanitization.py",
        ],
    },
    {
        "id": "AC-017",
        "summary": "Copilot answers with a grounded tool and matching figures",
        "kind": "suite",
        "evidence": [
            "apps/api/tests/integration/acceptance/test_ai.py::test_overspend_answer_uses_breakdown_and_matching_figures",
        ],
    },
    {
        "id": "AC-018",
        "summary": "Without data the copilot reports insufficiency",
        "kind": "suite",
        "evidence": [
            "apps/api/tests/integration/acceptance/test_ai.py::test_period_without_data_does_not_invent_causes",
        ],
    },
    {
        "id": "AC-019",
        "summary": "Mutation requests are refused; no mutable tool exists",
        "kind": "suite",
        "evidence": [
            "apps/api/tests/integration/acceptance/test_ai.py::test_mutation_request_is_refused_and_no_mutable_tool_exists",
        ],
    },
    {
        "id": "AC-020",
        "summary": "Prompt injection in a label does not change tenant or tools",
        "kind": "suite",
        "evidence": [
            "apps/api/tests/integration/acceptance/test_ai.py::test_injection_label_does_not_change_tenant",
        ],
    },
    {
        "id": "AC-021",
        "summary": "Altered tool args cannot target another tenant",
        "kind": "suite",
        "evidence": [
            "apps/api/tests/integration/acceptance/test_ai.py::test_altered_tool_args_cannot_retarget_another_tenant",
        ],
    },
    {
        "id": "AC-022",
        "summary": "Unbounded tool loops stop at the configured limit",
        "kind": "suite",
        "evidence": [
            "apps/api/tests/integration/acceptance/test_ai.py::test_unbounded_tool_loop_stops_and_records_a_metric",
        ],
    },
    {
        "id": "AC-023",
        "summary": "Readiness is 200 with DB and 503 without; liveness stays 200",
        "kind": "suite",
        "evidence": [
            "apps/api/tests/integration/acceptance/test_operations.py::test_readiness_fails_fast_when_database_is_down_and_liveness_stays_up",
            "apps/api/tests/unit/test_health_live.py",
            "apps/api/tests/unit/test_health_ready.py",
        ],
    },
    {
        "id": "AC-024",
        "summary": "Empty database and N-1 snapshot reach head",
        "kind": "suite",
        "evidence": [
            "apps/api/tests/integration/acceptance/test_operations.py::test_empty_and_n_minus_one_databases_reach_head",
        ],
    },
    {
        "id": "AC-025",
        "summary": "Application rollback restores the previous image without schema downgrade",
        "kind": "both",
        "evidence": [
            "docs/OPERATIONS.md#images-and-rollback",
            "scripts/acceptance-rollback.sh",
            "scripts/rollback-release.sh",
            ".github/workflows/deploy-dev.yml",
            "apps/api/tests/integration/acceptance/test_operations.py::test_application_rollback_keeps_the_previous_image_without_schema_downgrade",
        ],
    },
    {
        "id": "AC-026",
        "summary": "An isolated snapshot restore preserves counts and tenant invariants",
        "kind": "both",
        "evidence": [
            "docs/OPERATIONS.md#restore",
            "docs/DEPLOYMENT.md#restore-test",
            "scripts/acceptance-restore.sh",
            "scripts/restore-test.sh",
            "apps/api/tests/integration/acceptance/test_operations.py::test_isolated_restore_preserves_counts_and_tenant_invariants",
        ],
    },
]

PLANS: list[PlanRecord] = [
    {
        "id": "00",
        "name": "Bootstrap",
        "status": "complete",
        "requirements": ["FR-OPS-001", "FR-OPS-002", "NFR-MNT-002", "NFR-OBS-001"],
        "acceptance": ["AC-001", "AC-023", "AC-024"],
    },
    {
        "id": "01",
        "name": "Domain foundation",
        "status": "complete",
        "requirements": [
            "FR-ORG-001",
            "FR-ORG-002",
            "FR-ORG-003",
            "FR-ORG-004",
            "FR-ORG-005",
            "FR-DIM-001",
            "FR-DIM-002",
            "FR-DIM-003",
            "FR-BUD-001",
            "FR-BUD-002",
            "FR-BUD-003",
            "FR-BUD-004",
            "FR-AUD-001",
            "NFR-MNT-001",
            "NFR-MNT-003",
        ],
        "acceptance": ["AC-006", "AC-007", "AC-015"],
    },
    {
        "id": "02",
        "name": "Import pipeline",
        "status": "implemented",
        "requirements": [
            "FR-IMP-001",
            "FR-IMP-002",
            "FR-IMP-003",
            "FR-IMP-004",
            "FR-IMP-005",
            "FR-IMP-006",
            "FR-IMP-007",
            "FR-IMP-008",
            "FR-IMP-009",
            "FR-IMP-010",
            "FR-AUD-001",
            "NFR-PERF-003",
            "NFR-REL-003",
            "NFR-SEC-007",
            "NFR-PRI-001",
        ],
        "acceptance": ["AC-002", "AC-003", "AC-004", "AC-014"],
    },
    {
        "id": "03",
        "name": "Analytics",
        "status": "implemented",
        "requirements": [
            "FR-ANA-001",
            "FR-ANA-002",
            "FR-ANA-003",
            "FR-ANA-004",
            "FR-ANA-005",
            "FR-ANA-006",
            "FR-ANA-007",
            "FR-ANA-008",
            "FR-ANA-009",
            "NFR-PERF-001",
        ],
        "acceptance": ["AC-005", "AC-006", "AC-007", "AC-008", "AC-009", "AC-010"],
    },
    {
        "id": "04",
        "name": "Frontend",
        "status": "implemented",
        "requirements": [
            "FR-UI-001",
            "FR-UI-002",
            "FR-UI-003",
            "FR-UI-004",
            "FR-UI-005",
            "FR-ANA-003",
            "FR-ANA-006",
            "NFR-UX-001",
            "NFR-UX-002",
            "NFR-UX-003",
            "NFR-UX-004",
            "NFR-PERF-002",
        ],
        "acceptance": ["AC-002", "AC-005", "AC-008", "AC-009", "AC-010", "AC-013"],
    },
    {
        "id": "05",
        "name": "AI copilot",
        "status": "implemented",
        "requirements": [
            "FR-AI-001",
            "FR-AI-002",
            "FR-AI-003",
            "FR-AI-004",
            "FR-AI-005",
            "FR-AI-006",
            "FR-AI-007",
            "FR-AI-008",
            "FR-AI-009",
            "FR-AUD-002",
            "NFR-PERF-004",
            "NFR-SEC-004",
            "NFR-PRI-002",
            "NFR-PRI-004",
            "NFR-OBS-002",
        ],
        "acceptance": ["AC-017", "AC-018", "AC-019", "AC-020", "AC-021", "AC-022"],
    },
    {
        "id": "06",
        "name": "Auth and tenancy",
        "status": "implemented",
        "requirements": [
            "FR-ORG-002",
            "FR-ORG-003",
            "FR-ORG-004",
            "NFR-SEC-003",
            "NFR-SEC-004",
            "NFR-PRI-001",
        ],
        "acceptance": ["AC-011", "AC-012", "AC-013", "AC-014", "AC-015", "AC-016"],
    },
    {
        "id": "07",
        "name": "Hardening",
        "status": "implemented",
        "requirements": [
            "FR-AUD-001",
            "FR-AUD-003",
            "FR-OPS-001",
            "FR-OPS-002",
            "FR-OPS-003",
            "FR-OPS-004",
            "NFR-PERF-001",
            "NFR-PERF-003",
            "NFR-PERF-005",
            "NFR-REL-003",
            "NFR-REL-004",
            "NFR-REL-005",
            "NFR-SEC-005",
            "NFR-SEC-006",
            "NFR-PRI-003",
            "NFR-PRI-005",
            "NFR-MNT-005",
            "NFR-OBS-001",
            "NFR-OBS-002",
            "NFR-OBS-003",
            "NFR-OBS-004",
        ],
        "acceptance": ["AC-016", "AC-023", "AC-024", "AC-025"],
    },
    {
        "id": "08",
        "name": "Terraform",
        "status": "implemented",
        "requirements": [
            "NFR-SEC-001",
            "NFR-SEC-002",
            "NFR-REL-001",
            "NFR-MNT-006",
            "NFR-OBS-003",
        ],
        "acceptance": ["AC-025"],
    },
    {
        "id": "09",
        "name": "CI/CD",
        "status": "implemented",
        "requirements": ["NFR-SEC-002", "NFR-SEC-005", "NFR-REL-005", "NFR-MNT-004", "FR-OPS-004"],
        "acceptance": ["AC-001", "AC-025"],
    },
    {
        "id": "10",
        "name": "AWS deployment",
        "status": "implemented",
        "requirements": [
            "NFR-REL-001",
            "NFR-REL-002",
            "NFR-SEC-001",
            "FR-OPS-004",
            "NFR-OBS-003",
        ],
        "acceptance": ["AC-026"],
    },
    {
        "id": "11",
        "name": "Portfolio release",
        "status": "pending",
        "requirements": ["FR-OPS-004", "NFR-PRI-001"],
        "acceptance": ["AC-001"],
    },
]

GATES: list[GateRecord] = [
    {
        "id": "M-00",
        "name": "Functional defaults",
        "plans": ["01"],
        "owner": "Domain owner",
        "moment": "Before or during plan 01",
        "local_simulation": "Yes, defaults",
        "blocks": "No if defaults are accepted",
        "deliverables": [
            "fiscal year convention",
            "demo currency",
            "favorability rules",
            "actuals mode",
            "product language",
        ],
        "human_actions": [
            "Confirm fiscal-year convention, demo currency, favorability, "
            "actuals mode, and product language, or accept the spec defaults.",
        ],
        "blocks_release": [],
    },
    {
        "id": "M-01",
        "name": "Secure AWS account",
        "plans": ["08", "10"],
        "owner": "Security owner",
        "moment": "Before a real terraform plan",
        "local_simulation": "No",
        "blocks": "AWS",
        "deliverables": ["aws_account_id", "credential_method", "profile_or_role"],
        "human_actions": [
            "Create or select the account, enable root MFA, and record "
            "the account ID and temporary credential method.",
        ],
        "blocks_release": ["aws", "prod"],
    },
    {
        "id": "M-02",
        "name": "Region",
        "plans": ["05", "08", "09", "10"],
        "owner": "Operator",
        "moment": "Before remote bootstrap",
        "local_simulation": "Fake config",
        "blocks": "AWS",
        "deliverables": ["primary_region"],
        "human_actions": [
            "Choose the primary region after Bedrock, residency, latency, "
            "price, and ACM/CloudFront review.",
        ],
        "blocks_release": ["aws", "prod"],
    },
    {
        "id": "M-03",
        "name": "Budget",
        "plans": ["08", "09", "10"],
        "owner": "Operator",
        "moment": "Before apply",
        "local_simulation": "Terraform code",
        "blocks": "AWS",
        "deliverables": [
            "budget_limit",
            "alert_email",
            "email_subscription_confirmed",
            "cost_estimate_recorded",
        ],
        "human_actions": [
            "Choose limits, name the alert email, confirm the AWS subscription, "
            "and review a dated official estimate.",
        ],
        "blocks_release": ["aws", "prod"],
    },
    {
        "id": "M-04",
        "name": "Bedrock model access",
        "plans": ["05", "10"],
        "owner": "AI owner",
        "moment": "Live eval and AWS AI",
        "local_simulation": "Stub/contract mock",
        "blocks": "AWS AI",
        "deliverables": ["model_id"],
        "human_actions": [
            "Select a compatible model, request access if required, "
            "record the exact model ID, and approve live eval.",
        ],
        "blocks_release": ["aws", "prod"],
    },
    {
        "id": "M-05",
        "name": "GitHub/OIDC",
        "plans": ["09", "10"],
        "owner": "Engineering",
        "moment": "Real pipeline enablement",
        "local_simulation": "Workflow lint",
        "blocks": "Real pipeline",
        "deliverables": ["github_owner_repo", "environments_configured", "oidc_allowed"],
        "human_actions": [
            "Create the remote repository, protect main, "
            "create GitHub Environments, and allow OIDC.",
        ],
        "blocks_release": ["aws", "prod"],
    },
    {
        "id": "M-06",
        "name": "Domain/DNS",
        "plans": ["10", "11"],
        "owner": "Operator",
        "moment": "Before a final production URL",
        "local_simulation": "Managed domain",
        "blocks": "Production URL",
        "deliverables": ["domain_name", "dns_provider", "callback_urls"],
        "human_actions": [
            "Select the domain and DNS provider, authorize ACM/Cognito records, "
            "and define callback URLs.",
        ],
        "blocks_release": ["prod"],
    },
    {
        "id": "M-07",
        "name": "Users",
        "plans": ["06", "10"],
        "owner": "Security owner",
        "moment": "Before third-party users",
        "local_simulation": "Test issuer/JWKS",
        "blocks": "Third-party users",
        "deliverables": [
            "registration_mode",
            "mfa_policy",
            "account_recovery",
            "first_admin_process",
        ],
        "human_actions": [
            "Decide registration, MFA, recovery, and the first admin "
            "before opening Cognito to third parties.",
        ],
        "blocks_release": ["aws", "prod"],
    },
    {
        "id": "M-08",
        "name": "Data and chat policy",
        "plans": ["05", "10"],
        "owner": "Product/Security",
        "moment": "Before real data",
        "local_simulation": "Local synthetic policy",
        "blocks": "Real data",
        "deliverables": [
            "data_classification",
            "retention_policy",
            "conversation_persistence",
            "operator_access",
            "deletion_export_process",
        ],
        "human_actions": [
            "Accept classification, retention, conversation persistence, "
            "operator access, and deletion (ADR-012).",
        ],
        "blocks_release": ["aws", "prod"],
    },
    {
        "id": "M-09",
        "name": "Apply review",
        "plans": ["10"],
        "owner": "Operator",
        "moment": "Immediately before apply",
        "local_simulation": "No",
        "blocks": "AWS apply",
        "deliverables": [
            "aws_account",
            "aws_role",
            "aws_region",
            "plan_reviewed",
            "destroys_reviewed",
            "cost_estimate_reviewed",
            "image_digest",
            "migration_reviewed",
            "dns_callbacks_reviewed",
        ],
        "human_actions": [
            "Review identity, plan, estimate, digest, migration, and DNS, then authorize apply.",
        ],
        "blocks_release": ["aws", "prod"],
    },
    {
        "id": "M-10",
        "name": "Production",
        "plans": ["11"],
        "owner": "Owner",
        "moment": "Future production cutover",
        "local_simulation": "No",
        "blocks": "Production",
        "deliverables": [
            "prod_account_or_environment",
            "threat_privacy_review",
            "restore_test",
            "live_ai_eval",
            "incident_ownership",
            "plan_and_window_approved",
        ],
        "human_actions": [
            "Complete prod account, reviews, restore test, live AI eval, "
            "ownership, and an approved window.",
        ],
        "blocks_release": ["prod"],
    },
]

RISKS: list[RiskRecord] = [
    {
        "id": "R-01",
        "summary": "Incorrect calculation or rounding",
        "likelihood": "medium",
        "impact": "high",
        "mitigation": "Decimal amounts, pure rules, property-style cases, AC-005–010",
        "owner": "Domain owner",
        "trigger": "Difference against fixture or control total",
        "category": "quality",
        "mitigation_status": "verified",
        "evidence": [
            "apps/api/tests/unit/domain/test_variance.py",
            "apps/api/tests/unit/domain/test_money.py",
            "apps/api/tests/unit/domain/test_financial_properties.py",
        ],
        "blocks_release": [],
    },
    {
        "id": "R-02",
        "summary": "Cross-tenant leak",
        "likelihood": "medium",
        "impact": "high",
        "mitigation": "Tenant context, deny-by-default, isolation matrix, scoped storage/tools",
        "owner": "Security owner",
        "trigger": "IDOR test or audit anomaly",
        "category": "security",
        "mitigation_status": "verified",
        "evidence": [
            "apps/api/tests/integration/test_domain_api.py",
            "apps/api/tests/integration/test_personas_and_tenancy.py",
        ],
        "blocks_release": [],
    },
    {
        "id": "R-03",
        "summary": "Malicious or exhausting upload",
        "likelihood": "medium",
        "impact": "high",
        "mitigation": "Allowlist, size limits, no formulas/macros, timeouts",
        "owner": "Engineering",
        "trigger": "Parser crash or memory spike",
        "category": "security",
        "mitigation_status": "verified",
        "evidence": [
            "apps/api/tests/integration/test_import_and_analytics.py::test_formula_xlsx_is_rejected",
            "apps/api/tests/unit/test_large_preview.py",
            "apps/api/tests/unit/test_upload_boundaries.py::test_macro_enabled_workbook_is_rejected",
        ],
        "blocks_release": [],
    },
    {
        "id": "R-04",
        "summary": "Invented AI figures",
        "likelihood": "high",
        "impact": "high",
        "mitigation": "Registered tools, grounding, evidence, eval gate",
        "owner": "AI/Domain",
        "trigger": "Figure not present in tool output or safety fail",
        "category": "quality",
        "mitigation_status": "verified",
        "evidence": [
            "apps/api/tests/unit/test_ai_eval.py",
            "apps/api/tests/unit/domain/test_permissions_and_rules.py::test_ai_cannot_conclude_without_authorized_evidence",
        ],
        "blocks_release": [],
    },
    {
        "id": "R-05",
        "summary": "Prompt injection from imported data",
        "likelihood": "medium",
        "impact": "high",
        "mitigation": "Delimited data, closed tools, safety eval cases",
        "owner": "Security owner",
        "trigger": "Tool or tenant changes because of a label",
        "category": "security",
        "mitigation_status": "verified",
        "evidence": [
            "apps/api/src/budgetlens/application/ai_eval.py",
            "apps/api/tests/unit/test_ai_eval.py",
        ],
        "blocks_release": [],
    },
    {
        "id": "R-06",
        "summary": "Unexpected AWS cost",
        "likelihood": "medium",
        "impact": "high",
        "mitigation": "Budgets, tags, small dev sizing, teardown, measurement",
        "owner": "Operator",
        "trigger": "Forecast or actual exceeds the threshold",
        "category": "cost_external",
        "mitigation_status": "unverified",
        "evidence": [
            "docs/OPERATIONS.md",
            "infrastructure/terraform/bootstrap/main.tf",
            "infrastructure/terraform/environments/dev/terraform.tfvars",
            "scripts/record_cost_estimate.py",
            "scripts/teardown-environment.sh",
        ],
        "blocks_release": ["aws", "prod"],
    },
    {
        "id": "R-07",
        "summary": "NAT or RDS dominate demo cost",
        "likelihood": "high",
        "impact": "medium",
        "mitigation": "Measure, stop or destroy, record an alternative if needed",
        "owner": "Operator",
        "trigger": "Baseline week exceeds the cost objective",
        "category": "cost_external",
        "mitigation_status": "unverified",
        "evidence": [
            "docs/OPERATIONS.md",
            "infrastructure/terraform/environments/dev/terraform.tfvars",
            "scripts/teardown-environment.sh",
        ],
        "blocks_release": [],
    },
    {
        "id": "R-08",
        "summary": "Migration prevents rollback",
        "likelihood": "medium",
        "impact": "high",
        "mitigation": "Expand/contract, one-off jobs, N-1 upgrade tests",
        "owner": "Engineering",
        "trigger": "Deploy requires a schema downgrade",
        "category": "reliability",
        "mitigation_status": "verified",
        "evidence": ["apps/api/tests/integration/test_migrations.py", "docs/OPERATIONS.md"],
        "blocks_release": [],
    },
    {
        "id": "R-09",
        "summary": "Bedrock or the chosen model is unavailable",
        "likelihood": "medium",
        "impact": "medium",
        "mitigation": "Model config, stub provider, region gate, adapter",
        "owner": "AI owner",
        "trigger": "M-04 not completed",
        "category": "operations",
        "mitigation_status": "verified",
        "evidence": [
            "apps/api/tests/unit/test_ai_eval.py",
            "apps/api/src/budgetlens/application/ai.py",
        ],
        "blocks_release": [],
    },
    {
        "id": "R-10",
        "summary": "API change breaks the frontend",
        "likelihood": "medium",
        "impact": "medium",
        "mitigation": "OpenAPI snapshot and client drift gate",
        "owner": "Engineering",
        "trigger": "CI contract failure",
        "category": "quality",
        "mitigation_status": "verified",
        "evidence": [
            "apps/api/tests/unit/test_openapi.py",
            "packages/api-client/openapi.json",
            ".github/workflows/ci.yml",
        ],
        "blocks_release": [],
    },
    {
        "id": "R-11",
        "summary": "Performance degrades at 250k rows",
        "likelihood": "medium",
        "impact": "medium",
        "mitigation": "SQL aggregates, indexes from EXPLAIN, load tests",
        "owner": "Engineering",
        "trigger": "p95 misses the read threshold",
        "category": "quality",
        "mitigation_status": "partial",
        "evidence": ["scripts/load_test.py", "docs/OPERATIONS.md"],
        "blocks_release": [],
    },
    {
        "id": "R-12",
        "summary": "Secret in a log, state file, or build",
        "likelihood": "medium",
        "impact": "high",
        "mitigation": "Secret tests and scans, OIDC, sensitive outputs",
        "owner": "Security owner",
        "trigger": "Scanner or log assertion",
        "category": "security",
        "mitigation_status": "verified",
        "evidence": ["apps/api/tests/unit/test_logging_sanitization.py", "scripts/scan.sh"],
        "blocks_release": [],
    },
    {
        "id": "R-13",
        "summary": "Excess design delays the MVP",
        "likelihood": "medium",
        "impact": "medium",
        "mitigation": "Must/Should/Could, one plan at a time",
        "owner": "Product",
        "trigger": "Could work starts before Must work",
        "category": "product",
        "mitigation_status": "verified",
        "evidence": ["docs/BACKLOG.md", "docs/TRACEABILITY.md"],
        "blocks_release": [],
    },
    {
        "id": "R-14",
        "summary": "Dependency or provider change",
        "likelihood": "medium",
        "impact": "medium",
        "mitigation": "Lockfiles, adapters, decision record, eval on upgrade",
        "owner": "Engineering",
        "trigger": "Renovate or provider update",
        "category": "quality",
        "mitigation_status": "verified",
        "evidence": ["apps/api/uv.lock", "pnpm-lock.yaml", "docs/DECISIONS.md"],
        "blocks_release": [],
    },
    {
        "id": "R-15",
        "summary": "Backups are not restorable",
        "likelihood": "low",
        "impact": "high",
        "mitigation": "Isolated restore runbook (AC-026)",
        "owner": "Operator",
        "trigger": "Restore test fails",
        "category": "reliability",
        "mitigation_status": "unverified",
        "evidence": ["docs/OPERATIONS.md", "docs/DEPLOYMENT.md", "scripts/restore-test.sh"],
        "blocks_release": ["aws", "prod"],
    },
    {
        "id": "R-16",
        "summary": "Dev auth reaches the cloud",
        "likelihood": "low",
        "impact": "high",
        "mitigation": "Startup invariant AC-015",
        "owner": "Security owner",
        "trigger": "Forbidden config combination detected",
        "category": "security",
        "mitigation_status": "verified",
        "evidence": [
            "apps/api/tests/unit/test_dev_auth.py::test_create_app_rejects_dev_auth_in_prod",
            "apps/api/tests/unit/test_config.py::test_prod_rejects_dev_auth",
        ],
        "blocks_release": [],
    },
    {
        "id": "R-17",
        "summary": "Personal or real information in the demo",
        "likelihood": "medium",
        "impact": "high",
        "mitigation": "Synthetic-only seed, repository and log review",
        "owner": "Product/Security",
        "trigger": "Scan or review finds real data",
        "category": "privacy",
        "mitigation_status": "verified",
        "evidence": ["apps/api/src/budgetlens/seed.py", "scripts/scan.sh", ".gitignore"],
        "blocks_release": [],
    },
    {
        "id": "R-18",
        "summary": "Single-person project without operational capacity",
        "likelihood": "medium",
        "impact": "medium",
        "mitigation": "Runbooks, simple architecture, alerts",
        "owner": "Owner",
        "trigger": "Incident that the runbook cannot resolve",
        "category": "operations",
        "mitigation_status": "partial",
        "evidence": ["docs/OPERATIONS.md", "docs/DEPLOYMENT.md"],
        "blocks_release": [],
    },
]

BACKLOG: list[BacklogItem] = [
    {
        "id": "BL-1101",
        "summary": "Archive an organization from the UI without physical delete",
        "source": "FR-ORG-005",
        "priority": "should",
    },
    {
        "id": "BL-1102",
        "summary": "Explicitly replace an existing import data range",
        "source": "FR-IMP-010",
        "priority": "should",
    },
    {
        "id": "BL-1103",
        "summary": "Statistical forecast with backtesting",
        "source": "release-1.1",
        "priority": "could",
    },
    {
        "id": "BL-1104",
        "summary": "Multi-currency with an exchange-rate table",
        "source": "release-1.1",
        "priority": "could",
    },
    {
        "id": "BL-1105",
        "summary": "4-4-5 fiscal calendar",
        "source": "release-1.1",
        "priority": "could",
    },
    {
        "id": "BL-1106",
        "summary": "ERP integrations",
        "source": "release-1.1",
        "priority": "could",
    },
    {
        "id": "BL-1107",
        "summary": "Executive PDF or PowerPoint export",
        "source": "release-1.1",
        "priority": "could",
    },
    {
        "id": "BL-1108",
        "summary": "Scheduled alerts",
        "source": "release-1.1",
        "priority": "could",
    },
    {
        "id": "BL-1109",
        "summary": "Comments and approvals",
        "source": "release-1.1",
        "priority": "could",
    },
    {
        "id": "BL-1110",
        "summary": "Managed queues or workers if volume requires them",
        "source": "release-1.1",
        "priority": "could",
    },
]

DOC_PATHS: tuple[Path, ...] = (
    REPO_ROOT / "docs" / "TRACEABILITY.md",
    REPO_ROOT / "docs" / "RISKS.md",
    REPO_ROOT / "docs" / "BACKLOG.md",
    REPO_ROOT / "docs" / "DECISIONS.md",
    REPO_ROOT / "docs" / "OPERATIONS.md",
    REPO_ROOT / "docs" / "CICD.md",
    REPO_ROOT / "docs" / "GATES.md",
    REPO_ROOT / "docs" / "DEPLOYMENT.md",
)


def expected_functional_ids() -> list[str]:
    return [
        *[f"FR-ORG-{index:03d}" for index in range(1, 6)],
        *[f"FR-DIM-{index:03d}" for index in range(1, 4)],
        *[f"FR-BUD-{index:03d}" for index in range(1, 5)],
        *[f"FR-IMP-{index:03d}" for index in range(1, 11)],
        *[f"FR-ANA-{index:03d}" for index in range(1, 10)],
        *[f"FR-AI-{index:03d}" for index in range(1, 10)],
        *[f"FR-AUD-{index:03d}" for index in range(1, 4)],
        *[f"FR-OPS-{index:03d}" for index in range(1, 5)],
        *[f"FR-UI-{index:03d}" for index in range(1, 6)],
    ]


def expected_nfr_ids() -> list[str]:
    return [
        *[f"NFR-PERF-{index:03d}" for index in range(1, 6)],
        *[f"NFR-REL-{index:03d}" for index in range(1, 6)],
        *[f"NFR-SEC-{index:03d}" for index in range(1, 8)],
        *[f"NFR-PRI-{index:03d}" for index in range(1, 6)],
        *[f"NFR-UX-{index:03d}" for index in range(1, 5)],
        *[f"NFR-MNT-{index:03d}" for index in range(1, 7)],
        *[f"NFR-OBS-{index:03d}" for index in range(1, 5)],
    ]


def expected_acceptance_ids() -> list[str]:
    return [f"AC-{index:03d}" for index in range(1, 27)]


def expected_gate_ids() -> list[str]:
    return [f"M-{index:02d}" for index in range(0, 11)]


def expected_risk_ids() -> list[str]:
    return [f"R-{index:02d}" for index in range(1, 19)]


def expected_plan_ids() -> list[str]:
    return [f"{index:02d}" for index in range(0, 12)]


def requirement_by_id(requirement_id: str) -> FunctionalRequirement | NonFunctionalRequirement:
    for item in FUNCTIONAL_REQUIREMENTS:
        if item["id"] == requirement_id:
            return item
    for item in NON_FUNCTIONAL_REQUIREMENTS:
        if item["id"] == requirement_id:
            return item
    raise KeyError(requirement_id)


def acceptance_by_id(acceptance_id: str) -> AcceptanceCriterion:
    for item in ACCEPTANCE_CRITERIA:
        if item["id"] == acceptance_id:
            return item
    raise KeyError(acceptance_id)


def split_evidence(reference: str) -> tuple[str, str | None]:
    path, separator, symbol = reference.partition("::")
    if separator:
        return path, symbol
    path, separator, heading = reference.partition("#")
    if separator:
        return path, heading
    return reference, None


def evidence_exists(reference: str) -> bool:
    relative, marker = split_evidence(reference)
    path = REPO_ROOT / relative
    if not path.is_file():
        return False
    if marker is None:
        return True
    text = path.read_text(encoding="utf-8")
    slug = marker.replace("-", " ")
    return marker in text or slug.lower() in text.lower() or f"def {marker}" in text


def risk_release_blockers(scope: ReleaseScope) -> list[str]:
    blockers: list[str] = []
    for risk in RISKS:
        if risk["impact"] != "high":
            continue
        if risk["mitigation_status"] == "verified":
            continue
        if risk.get("accepted_by"):
            continue
        if scope in risk["blocks_release"]:
            blockers.append(risk["id"])
    return blockers


def gate_release_blockers(scope: ReleaseScope) -> list[str]:
    return [gate["id"] for gate in GATES if scope in gate["blocks_release"]]


def release_blockers(scope: ReleaseScope) -> list[str]:
    return [*risk_release_blockers(scope), *gate_release_blockers(scope)]


def deferred_requirements() -> list[FunctionalRequirement]:
    return [item for item in FUNCTIONAL_REQUIREMENTS if item["status"] == "deferred"]
