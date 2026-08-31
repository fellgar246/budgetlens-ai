from __future__ import annotations

import json
import os
import sys

from budgetlens.adapters.db import session_scope
from budgetlens.adapters.storage import LocalObjectStorage
from budgetlens.application.retention import purge_expired_originals
from budgetlens.application.watchdog import timeout_stale_jobs
from budgetlens.config import get_settings
from budgetlens.domain.identities import SystemClock, Uuid4Factory
from budgetlens.seed import run_seed

DEFAULT_EVAL_DATABASE_URL = (
    "postgresql+psycopg://budgetlens:budgetlens_local_only@127.0.0.1:5433/budgetlens"
)


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    if args == ["seed"]:
        run_seed()
        print("Seed applied.")
        return
    if args == ["eval-ai"]:
        os.environ.setdefault("APP_ENV", "test")
        os.environ.setdefault("AUTH_MODE", "dev")
        os.environ.setdefault("DATABASE_URL", DEFAULT_EVAL_DATABASE_URL)
        from budgetlens.application.ai_eval import run_stub_eval
        from budgetlens.config import reset_settings_cache

        reset_settings_cache()
        result = run_stub_eval()
        print(json.dumps(result, indent=2, ensure_ascii=True))
        passed = result["passed"]
        total = result["total"]
        if not isinstance(passed, int) or not isinstance(total, int) or passed != total:
            raise SystemExit(1)
        return
    if args == ["watchdog"]:
        settings = get_settings()
        with session_scope() as session:
            timed_out = timeout_stale_jobs(
                session,
                clock=SystemClock(),
                ids=Uuid4Factory(),
                settings=settings,
            )
        print(json.dumps({"timed_out": timed_out}, ensure_ascii=True))
        return
    if args == ["retain-files"]:
        settings = get_settings()
        with session_scope() as session:
            purged = purge_expired_originals(
                session,
                LocalObjectStorage(settings.local_storage_path),
                clock=SystemClock(),
                settings=settings,
            )
        print(json.dumps({"purged": purged}, ensure_ascii=True))
        return
    raise SystemExit("Usage: python -m budgetlens seed|eval-ai|watchdog|retain-files")
