from __future__ import annotations

import json
import re
from pathlib import Path

from budgetlens.presentation.app import create_app

SNAPSHOT = Path(__file__).resolve().parents[4] / "packages" / "api-client" / "openapi.json"
CLIENT = Path(__file__).resolve().parents[4] / "packages" / "api-client" / "src" / "index.ts"
PATH_TEMPLATE = re.compile(r"API_PREFIX\}/([^`\"'?]+)")
CAMEL = re.compile(r"(?<!^)(?=[A-Z])")


def _snake(value: str) -> str:
    return CAMEL.sub("_", value).lower()


def _client_paths() -> set[str]:
    found: set[str] = set()
    for raw in PATH_TEMPLATE.findall(CLIENT.read_text(encoding="utf-8")):
        path = "/api/v1/" + raw
        path = re.sub(r"\$\{([^}]+)\}", lambda match: "{" + _snake(match.group(1)) + "}", path)
        found.add(path.rstrip("/"))
    return found


def test_openapi_snapshot_matches_application(env_settings: None) -> None:
    del env_settings
    generated = create_app().openapi()
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert generated == snapshot


def test_typescript_client_paths_exist_in_the_snapshot() -> None:
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    documented = {path.rstrip("/") for path in snapshot.get("paths", {})}
    missing = sorted(path for path in _client_paths() if path not in documented)
    assert missing == []
