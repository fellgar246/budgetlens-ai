from __future__ import annotations

from typing import Protocol

from budgetlens.domain.organization import User


class IdentityProvider(Protocol):
    def authenticate(self, token: str) -> User: ...
