#!/usr/bin/env python3
"""Write the FastAPI OpenAPI document to the committed client snapshot."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "apps" / "api" / "src"
SNAPSHOT = ROOT / "packages" / "api-client" / "openapi.json"

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("AUTH_MODE", "dev")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://budgetlens:budgetlens_local_only@localhost:5432/budgetlens",
)

if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

from budgetlens.presentation.app import create_app  # noqa: E402


def main() -> None:
    app = create_app()
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {SNAPSHOT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
