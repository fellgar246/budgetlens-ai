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


class ScenarioOperation(StrEnum):
    PERCENTAGE_CHANGE = "percentage_change"
    ABSOLUTE_CHANGE = "absolute_change"


class ScenarioType(StrEnum):
    BUDGET = "budget"
    ACTUAL = "actual"


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


PNL_ACCOUNT_TYPES: frozenset[AccountType] = frozenset({AccountType.REVENUE, AccountType.EXPENSE})

UNASSIGNED_CODE = "UNASSIGNED"
ACCOUNT_HIERARCHY_MAX_DEPTH = 5
MONEY_SCALE = 4
RATIO_SCALE = 6
