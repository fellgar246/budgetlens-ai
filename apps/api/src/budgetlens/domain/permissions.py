from __future__ import annotations

from budgetlens.domain.enums import Capability, Permission, Persona, PlatformRole, Role
from budgetlens.domain.errors import PermissionDeniedError

_VIEWER = frozenset(
    {
        Permission.READ_ANALYSIS,
        Permission.EXPORT,
        Permission.USE_AI,
    }
)
_ANALYST = _VIEWER | frozenset(
    {
        Permission.IMPORT,
        Permission.MANAGE_VERSIONS,
        Permission.CREATE_SCENARIOS,
        Permission.MANAGE_DIMENSIONS,
    }
)
_ADMIN = _ANALYST | frozenset(
    {
        Permission.MANAGE_MEMBERS,
        Permission.MANAGE_ORGANIZATION,
    }
)
_OPERATOR = frozenset(
    {
        Permission.VIEW_TECHNICAL_METRICS,
        Permission.DEPLOY_ROLLBACK,
    }
)

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.VIEWER: _VIEWER,
    Role.ANALYST: _ANALYST,
    Role.ADMIN: _ADMIN,
}

PERSONA_CAPABILITIES: dict[Persona, frozenset[Capability]] = {
    Persona.BUDGET_OWNER: frozenset(
        {
            Capability.VIEW_DASHBOARD,
            Capability.USE_COPILOT,
        }
    ),
    Persona.FPNA_ANALYST: frozenset(
        {
            Capability.VIEW_DASHBOARD,
            Capability.IMPORT_ACTUALS,
            Capability.PUBLISH_BUDGET,
            Capability.CREATE_SCENARIO,
            Capability.USE_COPILOT,
        }
    ),
    Persona.ORGANIZATION_ADMIN: frozenset(
        {
            Capability.VIEW_DASHBOARD,
            Capability.IMPORT_ACTUALS,
            Capability.PUBLISH_BUDGET,
            Capability.CREATE_SCENARIO,
            Capability.USE_COPILOT,
            Capability.MANAGE_MEMBERS,
        }
    ),
    Persona.PLATFORM_OPERATOR: frozenset(
        {
            Capability.VIEW_TECHNICAL_METRICS,
            Capability.DEPLOY_ROLLBACK,
        }
    ),
}

_ROLE_PERSONA: dict[Role, Persona] = {
    Role.VIEWER: Persona.BUDGET_OWNER,
    Role.ANALYST: Persona.FPNA_ANALYST,
    Role.ADMIN: Persona.ORGANIZATION_ADMIN,
}


def permissions_for(role: Role) -> frozenset[Permission]:
    return ROLE_PERMISSIONS[role]


def granted_permissions(
    *,
    role: Role | None,
    platform_role: PlatformRole | None = None,
) -> frozenset[Permission]:
    granted: frozenset[Permission] = (
        permissions_for(role) if role is not None else frozenset[Permission]()
    )
    if platform_role is PlatformRole.OPERATOR:
        granted = granted | _OPERATOR
    return granted


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS[role]


def require_permission(role: Role, permission: Permission) -> None:
    if not has_permission(role, permission):
        raise PermissionDeniedError()


def persona_for(
    *,
    role: Role | None,
    platform_role: PlatformRole | None = None,
) -> Persona | None:
    if role is not None:
        return _ROLE_PERSONA[role]
    if platform_role is PlatformRole.OPERATOR:
        return Persona.PLATFORM_OPERATOR
    return None


def capabilities_for_persona(
    persona: Persona,
    *,
    owner_can_create_scenarios: bool = False,
) -> frozenset[Capability]:
    granted = PERSONA_CAPABILITIES[persona]
    if persona is Persona.BUDGET_OWNER and owner_can_create_scenarios:
        return granted | {Capability.CREATE_SCENARIO}
    return granted


def capabilities_for(
    *,
    role: Role | None,
    platform_role: PlatformRole | None = None,
    owner_can_create_scenarios: bool = False,
) -> frozenset[Capability]:
    persona = persona_for(role=role, platform_role=platform_role)
    if persona is None:
        return frozenset()
    return capabilities_for_persona(
        persona,
        owner_can_create_scenarios=owner_can_create_scenarios,
    )


def has_capability(
    *,
    role: Role | None,
    capability: Capability,
    platform_role: PlatformRole | None = None,
    owner_can_create_scenarios: bool = False,
) -> bool:
    return capability in capabilities_for(
        role=role,
        platform_role=platform_role,
        owner_can_create_scenarios=owner_can_create_scenarios,
    )


def require_capability(
    *,
    role: Role | None,
    capability: Capability,
    platform_role: PlatformRole | None = None,
    owner_can_create_scenarios: bool = False,
) -> None:
    if not has_capability(
        role=role,
        capability=capability,
        platform_role=platform_role,
        owner_can_create_scenarios=owner_can_create_scenarios,
    ):
        raise PermissionDeniedError()


def can_create_missing_dimensions(*, flag: bool, role: Role) -> bool:
    return flag and role is Role.ADMIN


def can_restructure_dimensions(role: Role) -> bool:
    return role is Role.ADMIN


def require_dimension_restructure(role: Role) -> None:
    if not can_restructure_dimensions(role):
        raise PermissionDeniedError()
