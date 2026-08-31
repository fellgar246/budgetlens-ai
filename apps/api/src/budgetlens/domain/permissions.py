from __future__ import annotations

from budgetlens.domain.enums import Permission, Role
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

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.VIEWER: _VIEWER,
    Role.ANALYST: _ANALYST,
    Role.ADMIN: _ADMIN,
}


def permissions_for(role: Role) -> frozenset[Permission]:
    return ROLE_PERMISSIONS[role]


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS[role]


def require_permission(role: Role, permission: Permission) -> None:
    if not has_permission(role, permission):
        raise PermissionDeniedError()


def can_create_missing_dimensions(*, flag: bool, role: Role) -> bool:
    return flag and role is Role.ADMIN
