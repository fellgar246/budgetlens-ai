from __future__ import annotations

import json
import os
import sys
from typing import cast
from uuid import UUID

from budgetlens.adapters.db import session_scope
from budgetlens.adapters.factory import (
    build_ai_provider,
    build_import_runner,
    build_object_storage,
    build_workbook_parser,
)
from budgetlens.adapters.persistence.finance_repositories import get_import_job
from budgetlens.adapters.persistence.repositories import (
    SqlMembershipRepository,
    SqlUserRepository,
)
from budgetlens.adapters.tenancy import apply_tenant_gucs
from budgetlens.application.ai_eval import run_stub_eval
from budgetlens.application.context import TenantContext
from budgetlens.application.imports import ImportService
from budgetlens.application.retention import purge_expired_conversations, purge_expired_originals
from budgetlens.application.watchdog import timeout_stale_jobs
from budgetlens.config import get_settings, reset_settings_cache
from budgetlens.domain.errors import NotFoundError
from budgetlens.domain.identities import SystemClock, Uuid4Factory

DEFAULT_EVAL_DATABASE_URL = (
    "postgresql+psycopg://budgetlens:budgetlens_local_only@127.0.0.1:5433/budgetlens"
)
USAGE = (
    "Usage: python -m budgetlens seed|eval-ai|watchdog|retain-files|"
    "import-job validate|apply <job-id>"
)


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    if args == ["seed"]:
        from budgetlens.seed import run_seed

        run_seed()
        print("Seed applied.")
        return
    if args == ["eval-ai"]:
        os.environ.setdefault("APP_ENV", "test")
        os.environ.setdefault("AUTH_MODE", "dev")
        os.environ.setdefault("DATABASE_URL", DEFAULT_EVAL_DATABASE_URL)
        reset_settings_cache()
        result = run_stub_eval(build_ai_provider(get_settings()))
        print(json.dumps(result, indent=2, ensure_ascii=True))
        passed = result["passed"]
        total = result["total"]
        gates = result.get("gates")
        gates_ok = False
        if isinstance(gates, dict):
            typed_gates = cast(dict[object, object], gates)
            gates_ok = all(bool(value) for value in typed_gates.values())
        if (
            not isinstance(passed, int)
            or not isinstance(total, int)
            or passed != total
            or not gates_ok
        ):
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
            clock = SystemClock()
            purged = purge_expired_originals(
                session,
                build_object_storage(settings),
                clock=clock,
                settings=settings,
            )
            conversations = purge_expired_conversations(session, clock=clock)
        print(
            json.dumps(
                {"purged": purged, "conversations_purged": conversations},
                ensure_ascii=True,
            )
        )
        return
    if len(args) == 3 and args[0] == "import-job":
        _run_import_job(operation=args[1], job_id=args[2])
        return
    raise SystemExit(USAGE)


def _run_import_job(*, operation: str, job_id: str) -> None:
    if operation not in {"validate", "apply"}:
        raise SystemExit(USAGE)
    settings = get_settings()
    parsed_id = UUID(job_id)
    with session_scope() as session:
        job = get_import_job(session, parsed_id)
        if job is None:
            raise NotFoundError()
        user = SqlUserRepository(session).get(job.created_by)
        if user is None:
            raise NotFoundError()
        apply_tenant_gucs(session, user_id=user.id, organization_id=job.organization_id)
        membership = SqlMembershipRepository(session, job.organization_id).get_for_user(user.id)
        if membership is None or not membership.is_active():
            raise NotFoundError()
        service = ImportService(
            session,
            SystemClock(),
            Uuid4Factory(),
            build_object_storage(settings),
            settings,
            build_import_runner(settings),
            build_workbook_parser(),
        )
        context = TenantContext(
            user=user,
            organization_id=job.organization_id,
            role=membership.role,
            trace_id=job.trace_id or "import-job",
        )
        if operation == "validate":
            raw_columns = job.mapping_json.get("columns") if job.mapping_json else None
            mapping: dict[str, str] = {}
            if isinstance(raw_columns, dict):
                mapping = {
                    str(key): str(value)
                    for key, value in cast(dict[object, object], raw_columns).items()
                }
            amount_locale = (
                str(job.mapping_json.get("amount_locale", "en")) if job.mapping_json else "en"
            )
            updated = service.validate(
                context,
                job_id=job.id,
                mapping=mapping,
                create_missing_dimensions=job.create_missing_dimensions,
                amount_locale=amount_locale,
            )
        else:
            updated = service.commit(context, job_id=job.id, idempotency_key=f"worker:{job.id}")
        print(
            json.dumps(
                {"id": str(updated.id), "status": updated.status.value, "operation": operation},
                ensure_ascii=True,
            )
        )
