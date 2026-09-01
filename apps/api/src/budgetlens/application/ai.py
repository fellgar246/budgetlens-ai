from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy.orm import Session

from budgetlens.adapters.persistence.finance_repositories import SqlConversationRepository
from budgetlens.adapters.persistence.repositories import (
    SqlAccountRepository,
    SqlAuditRepository,
    SqlDepartmentRepository,
)
from budgetlens.application.analytics import AnalyticsQuery, AnalyticsService, parse_analytics_query
from budgetlens.application.audit import record_audit
from budgetlens.application.context import TenantContext
from budgetlens.application.pagination import Page, clamp_limit
from budgetlens.application.rate_limit import enforce_limit
from budgetlens.application.scenarios import ScenarioService, as_object_map, parse_rule_payload
from budgetlens.config import Settings
from budgetlens.domain.conversation import (
    AiRun,
    Conversation,
    ToolExecution,
    normalize_message,
)
from budgetlens.domain.enums import (
    AiRunStatus,
    AnalyticsGroupBy,
    MessageRole,
    Permission,
    ScenarioType,
    ToolExecutionStatus,
)
from budgetlens.domain.errors import DomainError, NotFoundError, ValidationError
from budgetlens.domain.evidence import Evidence, evaluate_grounding
from budgetlens.domain.idempotency import canonical_json, sha256_hex
from budgetlens.domain.identities import Clock, IdFactory
from budgetlens.domain.money import Currency, MoneyAmount
from budgetlens.domain.organization import normalize_name
from budgetlens.domain.permissions import require_permission
from budgetlens.domain.scenario import ScenarioRule
from budgetlens.observability import metrics_registry
from budgetlens.ports.ai import AIProvider, ToolRequest

REGISTERED_TOOLS = frozenset(
    {
        "get_variance_summary",
        "get_variance_breakdown",
        "get_top_unfavorable_variances",
        "compare_periods",
        "calculate_scenario_preview",
    }
)
MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


@dataclass(frozen=True, slots=True)
class CopilotAnswer:
    message_id: UUID
    answer: str
    scope: dict[str, Any]
    evidence: list[dict[str, Any]]
    limitations: list[str]
    trace_id: str


class ConversationService:
    def __init__(
        self,
        session: Session,
        clock: Clock,
        ids: IdFactory,
        settings: Settings,
        analytics: AnalyticsService,
        scenarios: ScenarioService,
        provider: AIProvider,
    ) -> None:
        self._session = session
        self._clock = clock
        self._ids = ids
        self._settings = settings
        self._analytics = analytics
        self._scenarios = scenarios
        self._provider = provider
        self._audits = SqlAuditRepository(session)

    def _repo(self, organization_id: UUID) -> SqlConversationRepository:
        return SqlConversationRepository(self._session, organization_id)

    def list(
        self, context: TenantContext, *, cursor: str | None, limit: int | None
    ) -> Page[Conversation]:
        require_permission(context.role, Permission.USE_AI)
        return self._repo(context.organization_id).list_page(
            user_id=context.user.id, cursor=cursor, limit=clamp_limit(limit)
        )

    def create(
        self, context: TenantContext, *, title: str | None, filters: dict[str, Any]
    ) -> Conversation:
        require_permission(context.role, Permission.USE_AI)
        now = self._clock.now()
        conversation = Conversation(
            id=self._ids.new_id(),
            organization_id=context.organization_id,
            user_id=context.user.id,
            title=normalize_name(title or "Nueva conversación", field="title", max_length=160),
            context_filters=filters,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
        self._repo(context.organization_id).add(conversation)
        return conversation

    def get(self, context: TenantContext, conversation_id: UUID) -> Conversation:
        require_permission(context.role, Permission.USE_AI)
        conversation = self._repo(context.organization_id).get(conversation_id)
        if (
            conversation is None
            or conversation.is_deleted
            or conversation.user_id != context.user.id
        ):
            raise NotFoundError()
        return conversation

    def delete(self, context: TenantContext, conversation_id: UUID) -> Conversation:
        conversation = self.get(context, conversation_id)
        updated = conversation.soft_delete(now=self._clock.now())
        self._repo(context.organization_id).save(updated)
        record_audit(
            self._audits,
            clock=self._clock,
            ids=self._ids,
            organization_id=context.organization_id,
            actor_id=context.user.id,
            action="conversation.delete",
            resource_type="conversation",
            resource_id=conversation.id,
            trace_id=context.trace_id,
            metadata={"deleted": True},
        )
        return updated

    def ask(
        self,
        context: TenantContext,
        *,
        conversation_id: UUID,
        content: str,
        view_context: dict[str, Any],
    ) -> CopilotAnswer:
        require_permission(context.role, Permission.USE_AI)
        enforce_limit("ai", context.user.id, limit=self._settings.rate_limit_ai_per_minute)
        conversation = self.get(context, conversation_id)
        question = normalize_message(content)
        record_audit(
            self._audits,
            clock=self._clock,
            ids=self._ids,
            organization_id=context.organization_id,
            actor_id=context.user.id,
            action="ai.message_requested",
            resource_type="conversation",
            resource_id=conversation.id,
            trace_id=context.trace_id,
            metadata={"has_context": bool(view_context or conversation.context_filters)},
        )
        repo = self._repo(context.organization_id)
        now = self._clock.now()
        try:
            return self._complete_ask(
                context,
                conversation=conversation,
                question=question,
                view_context=view_context,
                repo=repo,
                now=now,
            )
        except DomainError as exc:
            record_audit(
                self._audits,
                clock=self._clock,
                ids=self._ids,
                organization_id=context.organization_id,
                actor_id=context.user.id,
                action="ai.response_failed",
                resource_type="conversation",
                resource_id=conversation.id,
                trace_id=context.trace_id,
                metadata={"code": exc.code},
                outcome="failed",
            )
            raise

    def _complete_ask(
        self,
        context: TenantContext,
        *,
        conversation: Conversation,
        question: str,
        view_context: dict[str, Any],
        repo: SqlConversationRepository,
        now: datetime,
    ) -> CopilotAnswer:
        user_message = conversation.message(
            message_id=self._ids.new_id(),
            role=MessageRole.USER,
            content=question,
            created_at=now,
        )
        repo.add_message(user_message)
        started = time.perf_counter()
        history = repo.list_messages(conversation.id, limit=self._settings.ai_max_context_turns)
        provider = self._provider.complete(
            messages=history, question=question, settings=self._settings
        )
        evidence: list[dict[str, Any]] = []
        figures: list[MoneyAmount] = []
        limitations: list[str] = []
        query = self._query_from_context(
            context, question, view_context or conversation.context_filters
        )
        tool_count = 0
        status = AiRunStatus.SUCCEEDED
        answer = provider.text or ""
        run_id = self._ids.new_id()
        pending_tools: list[ToolExecution] = []
        for request in provider.tool_requests:
            if tool_count >= self._settings.ai_max_tool_calls:
                status = AiRunStatus.LIMITED
                limitations.append(
                    "Se alcanzó el límite de herramientas. No entrego una conclusión parcial."
                )
                answer = "No pude completar la consulta dentro del límite de herramientas."
                break
            if request.name not in REGISTERED_TOOLS:
                continue
            tool_count += 1
            payload, row_count, status_tool = self._run_tool(context, request, query)
            evidence.append(
                {
                    "id": f"ev_{tool_count}",
                    "tool": request.name,
                    "label": _tool_label(request.name),
                    "data": payload,
                }
            )
            figures.extend(_extract_amounts(payload))
            execution = ToolExecution(
                id=self._ids.new_id(),
                organization_id=context.organization_id,
                ai_run_id=run_id,
                tool_name=request.name,
                argument_hash=sha256_hex(canonical_json(request.arguments).encode()),
                result_hash=sha256_hex(canonical_json(payload).encode()),
                row_count=row_count,
                duration_ms=0,
                status=status_tool,
            )
            pending_tools.append(execution)
            record_audit(
                self._audits,
                clock=self._clock,
                ids=self._ids,
                organization_id=context.organization_id,
                actor_id=context.user.id,
                action="ai.tool_executed",
                resource_type="conversation",
                resource_id=conversation.id,
                trace_id=context.trace_id,
                metadata={
                    "name": execution.tool_name,
                    "argument_hash": execution.argument_hash,
                    "result_hash": execution.result_hash,
                    "row_count": execution.row_count,
                },
            )
        grounding = (
            evaluate_grounding(
                [
                    Evidence(
                        tool_name=str(item["tool"]),
                        authorized=True,
                        period_from=query.period_from,
                        period_to=query.period_to,
                        budget_version_id=query.budget_version_id,
                        currency=Currency("MXN"),
                        figures=tuple(figures),
                    )
                    for item in evidence
                ]
            )
            if evidence
            else evaluate_grounding([])
        )
        if provider.tool_requests and not answer:
            if not grounding.can_conclude:
                answer = "No hay cifras suficientes en el alcance para concluir."
                limitations.append("Sin evidencia autorizada no se inventan causas ni importes.")
            else:
                answer = _answer_from_evidence(question, evidence)
        org = None
        del org
        latency_ms = int((time.perf_counter() - started) * 1000)
        run = AiRun(
            id=run_id,
            organization_id=context.organization_id,
            conversation_id=conversation.id,
            provider=self._settings.ai_provider,
            model_id=provider.model_id,
            latency_ms=latency_ms,
            input_units=provider.input_units,
            output_units=provider.output_units,
            status=status,
            trace_id=context.trace_id,
            created_at=self._clock.now(),
        )
        repo.add_run(run)
        for execution in pending_tools:
            repo.add_tool(execution)
        assistant = conversation.message(
            message_id=self._ids.new_id(),
            role=MessageRole.ASSISTANT,
            content=answer,
            created_at=self._clock.now(),
        )
        repo.add_message(assistant)
        record_audit(
            self._audits,
            clock=self._clock,
            ids=self._ids,
            organization_id=context.organization_id,
            actor_id=context.user.id,
            action="ai.response_completed",
            resource_type="conversation",
            resource_id=conversation.id,
            trace_id=context.trace_id,
            metadata={
                "latency_ms": latency_ms,
                "tools": [
                    {
                        "name": item.tool_name,
                        "argument_hash": item.argument_hash,
                        "result_hash": item.result_hash,
                    }
                    for item in pending_tools
                ],
            },
        )
        if latency_ms > self._settings.ai_timeout_seconds * 1000:
            limitations.append("La respuesta superó el tiempo máximo configurado.")
        metrics_registry().record_ai_run(
            latency_ms=latency_ms,
            input_units=provider.input_units,
            output_units=provider.output_units,
            tool_calls=len(pending_tools),
            tool_failures=sum(
                1 for item in pending_tools if item.status is not ToolExecutionStatus.SUCCEEDED
            ),
        )
        scope = {
            "fiscal_year": query.fiscal_year,
            "period_from": query.period_from.isoformat(),
            "period_to": query.period_to.isoformat(),
            "budget_version_id": str(query.budget_version_id),
            "currency": view_context.get("currency")
            or conversation.context_filters.get("currency"),
        }
        return CopilotAnswer(
            message_id=assistant.id,
            answer=answer,
            scope=scope,
            evidence=evidence,
            limitations=limitations,
            trace_id=context.trace_id,
        )

    def _query_from_context(
        self, context: TenantContext, question: str, raw: dict[str, Any]
    ) -> AnalyticsQuery:
        version = raw.get("budget_version_id")
        if not version:
            raise ValidationError(
                "INVALID_SCOPE",
                "El copiloto necesita una versión de presupuesto en el contexto.",
            )
        period_from = date.fromisoformat(str(raw.get("period_from") or "2026-01-01"))
        period_to = date.fromisoformat(str(raw.get("period_to") or "2026-12-01"))
        month = next((value for name, value in MONTHS.items() if name in question.lower()), None)
        if month is not None:
            period_from = date(period_from.year, month, 1)
            period_to = period_from
        if "ene-feb" in question.lower() or "enero y febrero" in question.lower():
            period_from = date(period_from.year, 1, 1)
            period_to = date(period_from.year, 2, 1)
        account_ids = [UUID(str(item)) for item in raw.get("account_ids", [])]
        department_ids = [UUID(str(item)) for item in raw.get("department_ids", [])]
        lowered = question.lower()
        account = _lookup_account(self._session, context.organization_id, lowered)
        if account is not None:
            account_ids = [account]
        department = _lookup_department(self._session, context.organization_id, lowered)
        if department is not None:
            department_ids = [department]
        return parse_analytics_query(
            fiscal_year=int(raw.get("fiscal_year") or period_from.year),
            period_from=period_from,
            period_to=period_to,
            budget_version_id=UUID(str(version)),
            account_ids=account_ids,
            department_ids=department_ids,
            cost_center_ids=[UUID(str(item)) for item in raw.get("cost_center_ids", [])],
        )

    def _run_tool(
        self,
        context: TenantContext,
        request: ToolRequest,
        query: AnalyticsQuery,
    ) -> tuple[dict[str, Any], int, ToolExecutionStatus]:
        arguments = dict(request.arguments)
        arguments.pop("organization_id", None)
        if request.name == "get_variance_summary":
            summary = self._analytics.summary(context, query)
            payload = {"scope": _scope(query), "metrics": summary.metrics.as_dict()}
            return payload, 1, ToolExecutionStatus.SUCCEEDED
        if request.name == "get_variance_breakdown":
            group_by = AnalyticsGroupBy(str(arguments.get("group_by", "account")))
            page = self._analytics.breakdown(
                context,
                query,
                group_by=group_by,
                sort=__import__(
                    "budgetlens.domain.enums", fromlist=["AnalyticsSort"]
                ).AnalyticsSort.ABSOLUTE_VARIANCE,
                direction=__import__(
                    "budgetlens.domain.enums", fromlist=["SortDirection"]
                ).SortDirection.DESC,
                cursor=None,
                limit=min(20, self._settings.ai_max_result_rows),
            )
            payload = {
                "scope": _scope(query),
                "items": [
                    {
                        "group_code": item.group_code,
                        "group_name": item.group_name,
                        **item.metrics.as_dict(),
                    }
                    for item in page.items
                ],
            }
            return payload, len(page.items), ToolExecutionStatus.SUCCEEDED
        if request.name == "get_top_unfavorable_variances":
            group_by = AnalyticsGroupBy(str(arguments.get("group_by", "account")))
            items = self._analytics.top_unfavorable(context, query, group_by=group_by, limit=10)
            payload = {
                "scope": _scope(query),
                "items": [
                    {
                        "group_code": item.group_code,
                        "group_name": item.group_name,
                        **item.metrics.as_dict(),
                    }
                    for item in items
                ],
            }
            return payload, len(items), ToolExecutionStatus.SUCCEEDED
        if request.name == "compare_periods":
            year = query.period_from.year
            compared = self._analytics.compare_periods(
                context,
                AnalyticsQuery(
                    fiscal_year=query.fiscal_year,
                    period_from=date(year, 1, 1),
                    period_to=date(year, 1, 1),
                    budget_version_id=query.budget_version_id,
                    account_ids=query.account_ids,
                    department_ids=query.department_ids,
                    cost_center_ids=query.cost_center_ids,
                ),
                compare_from=date(year, 2, 1),
                compare_to=date(year, 2, 1),
            )
            payload = {
                "baseline": compared["baseline"].metrics.as_dict(),
                "comparison": compared["comparison"].metrics.as_dict(),
            }
            return payload, 2, ToolExecutionStatus.SUCCEEDED
        if request.name == "calculate_scenario_preview":
            rules_raw = arguments.get("rules", [])
            rules: list[ScenarioRule] = []
            if isinstance(rules_raw, list):
                for item in cast(list[object], rules_raw):
                    if isinstance(item, dict):
                        rules.append(parse_rule_payload(as_object_map(cast(object, item))))
            payload = self._scenarios.preview(
                context,
                query=query,
                baseline_type=ScenarioType.BUDGET,
                rules=rules,
            )
            return payload, 1, ToolExecutionStatus.SUCCEEDED
        raise ValidationError("UNKNOWN_TOOL", "La herramienta solicitada no está registrada.")


def _scope(query: AnalyticsQuery) -> dict[str, str]:
    return {
        "fiscal_year": str(query.fiscal_year),
        "period_from": query.period_from.isoformat(),
        "period_to": query.period_to.isoformat(),
        "budget_version_id": str(query.budget_version_id),
    }


def _tool_label(name: str) -> str:
    labels = {
        "get_variance_summary": "Resumen de variación",
        "get_variance_breakdown": "Desglose",
        "get_top_unfavorable_variances": "Principales desfavorables",
        "compare_periods": "Comparación de periodos",
        "calculate_scenario_preview": "Vista previa de escenario",
    }
    return labels.get(name, name)


def _extract_amounts(payload: dict[str, Any]) -> list[MoneyAmount]:
    found: list[MoneyAmount] = []

    def walk(value: object) -> None:
        if isinstance(value, dict):
            for key, item in cast(dict[str, object], value).items():
                if key.endswith("_amount") and isinstance(item, str):
                    found.append(MoneyAmount(item))
                else:
                    walk(item)
        elif isinstance(value, list):
            for item in cast(list[object], value):
                walk(item)

    walk(payload)
    return found


def _answer_from_evidence(question: str, evidence: list[dict[str, Any]]) -> str:
    first = evidence[0]["data"]
    if "metrics" in first:
        metrics = first["metrics"]
        return (
            f"Según el resumen, presupuesto {metrics['budget_amount']}, "
            f"real {metrics['actual_amount']}, variación {metrics['variance_amount']} "
            f"({metrics['favorability']}, {metrics['variance_state']})."
        )
    if "items" in first and first["items"]:
        top = first["items"][0]
        return (
            f"El principal contribuyente es {top.get('group_name') or top.get('group_code')} "
            f"con variación {top.get('variance_amount')} ({top.get('favorability')})."
        )
    if "baseline" in first and "comparison" in first:
        return (
            f"En el primer periodo la variación fue {first['baseline']['variance_amount']}; "
            f"en el segundo fue {first['comparison']['variance_amount']}."
        )
    if "marketing" in question.lower():
        return "No hay una dimensión de marketing en el alcance. No invento cifras."
    return "Consulté las herramientas autorizadas y no hay una conclusión adicional."


def _lookup_account(session: Session, organization_id: UUID, text: str) -> UUID | None:
    repo = SqlAccountRepository(session, organization_id)
    page = repo.list_page(cursor=None, limit=100, status=None, search=None)
    for item in page.items:
        if item.name.lower() in text or item.code.lower() in text:
            return item.id
    return None


def _lookup_department(session: Session, organization_id: UUID, text: str) -> UUID | None:
    repo = SqlDepartmentRepository(session, organization_id)
    page = repo.list_page(cursor=None, limit=100, status=None, search=None)
    for item in page.items:
        if item.name.lower() in text or item.code.lower() in text:
            return item.id
    return None
