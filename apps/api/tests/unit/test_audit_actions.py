from __future__ import annotations

from pathlib import Path

from budgetlens import domain
from budgetlens.domain import audit as audit_module

API_SRC = Path(domain.__file__).resolve().parents[1]


def test_declared_audit_actions_are_emitted() -> None:
    actions = {
        name: value
        for name, value in vars(audit_module).items()
        if name.isupper() and isinstance(value, str) and "." in value
    }
    assert "AUTH_LOGIN_SUCCEEDED" in actions
    assert "IMPORT_CREATED" in actions
    assert "AI_MESSAGE_REQUESTED" in actions
    blobs = [
        path.read_text(encoding="utf-8")
        for folder in ("application", "adapters", "presentation")
        for path in (API_SRC / folder).rglob("*.py")
    ]
    blobs.append((API_SRC / "seed.py").read_text(encoding="utf-8"))
    combined = "\n".join(blobs)
    missing = [name for name in sorted(actions) if name not in combined]
    assert missing == []
