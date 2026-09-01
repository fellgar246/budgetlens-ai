from __future__ import annotations

from enum import StrEnum


class AccountType(StrEnum):
    REVENUE = "revenue"
    EXPENSE = "expense"
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    OTHER = "other"


class VarianceState(StrEnum):
    DEFINED = "defined"
    NO_ACTIVITY = "no_activity"
    UNBOUNDED = "unbounded"


class Favorability(StrEnum):
    FAVORABLE = "favorable"
    UNFAVORABLE = "unfavorable"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


class BudgetVersionStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class OrganizationStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class DimensionStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Role(StrEnum):
    VIEWER = "viewer"
    ANALYST = "analyst"
    ADMIN = "admin"


class PlatformRole(StrEnum):
    OPERATOR = "operator"


class Persona(StrEnum):
    BUDGET_OWNER = "budget_owner"
    FPNA_ANALYST = "fpna_analyst"
    ORGANIZATION_ADMIN = "organization_admin"
    PLATFORM_OPERATOR = "platform_operator"


class Capability(StrEnum):
    VIEW_DASHBOARD = "view_dashboard"
    IMPORT_ACTUALS = "import_actuals"
    PUBLISH_BUDGET = "publish_budget"
    CREATE_SCENARIO = "create_scenario"
    USE_COPILOT = "use_copilot"
    MANAGE_MEMBERS = "manage_members"
    VIEW_TECHNICAL_METRICS = "view_technical_metrics"
    DEPLOY_ROLLBACK = "deploy_rollback"


class ScenarioOperation(StrEnum):
    PERCENTAGE_CHANGE = "percentage_change"
    ABSOLUTE_CHANGE = "absolute_change"


class ScenarioType(StrEnum):
    BUDGET = "budget"
    ACTUAL = "actual"


class ImportJobStatus(StrEnum):
    CREATED = "created"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    INVALID = "invalid"
    APPLIED = "applied"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ImportErrorSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class ExportJobStatus(StrEnum):
    READY = "ready"
    EXPIRED = "expired"


class ExportType(StrEnum):
    VARIANCE_BREAKDOWN = "variance_breakdown"
    IMPORT_ERRORS = "import_errors"


class ScenarioStatus(StrEnum):
    DRAFT = "draft"
    SAVED = "saved"
    ARCHIVED = "archived"


class AnalyticsGroupBy(StrEnum):
    PERIOD = "period"
    ACCOUNT = "account"
    DEPARTMENT = "department"
    COST_CENTER = "cost_center"


class AnalyticsSort(StrEnum):
    VARIANCE_AMOUNT = "variance_amount"
    ABSOLUTE_VARIANCE = "absolute_variance"
    BUDGET_AMOUNT = "budget_amount"
    ACTUAL_AMOUNT = "actual_amount"


class SortDirection(StrEnum):
    ASC = "asc"
    DESC = "desc"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class AiRunStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    LIMITED = "limited"
    GROUNDING_FAILED = "grounding_failed"


class ToolExecutionStatus(StrEnum):
    SUCCEEDED = "succeeded"
    REJECTED = "rejected"
    FAILED = "failed"


class Permission(StrEnum):
    READ_ANALYSIS = "read_analysis"
    EXPORT = "export"
    USE_AI = "use_ai"
    IMPORT = "import"
    MANAGE_VERSIONS = "manage_versions"
    CREATE_SCENARIOS = "create_scenarios"
    MANAGE_DIMENSIONS = "manage_dimensions"
    MANAGE_MEMBERS = "manage_members"
    MANAGE_ORGANIZATION = "manage_organization"
    VIEW_TECHNICAL_METRICS = "view_technical_metrics"
    DEPLOY_ROLLBACK = "deploy_rollback"


PNL_ACCOUNT_TYPES: frozenset[AccountType] = frozenset({AccountType.REVENUE, AccountType.EXPENSE})

UNASSIGNED_CODE = "UNASSIGNED"
ACCOUNT_HIERARCHY_MAX_DEPTH = 5
MONEY_SCALE = 4
RATIO_SCALE = 6
