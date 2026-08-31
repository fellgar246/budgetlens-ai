from __future__ import annotations

import json
from pathlib import Path

from budgetlens.presentation.app import create_app

SNAPSHOT = Path(__file__).resolve().parents[4] / "packages" / "api-client" / "openapi.json"


def test_openapi_snapshot_matches_application(env_settings: None) -> None:
    del env_settings
    generated = create_app().openapi()
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert generated == snapshot
