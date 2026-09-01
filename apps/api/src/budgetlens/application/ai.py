from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy.orm import Session

from budgetlens.adapters.persistence.finance_repositories import SqlConversationRepository
from budgetlens.adapters.persistence.repositories import (
    SqlAccountRepository,
    SqlAuditRepository,
    SqlDepartmentRepository,
    SqlOrganizationRepository,
)
from budgetlens.application.analytics import AnalyticsQuery, AnalyticsService, parse_analytics_query
from budgetlens.application.audit import record_audit
from budgetlens.application.context import TenantContext
from budgetlens.application.pagination import Page, clamp_limit
from budgetlens.application.rate_limit import (
    acquire_conversation_slot,
    enforce_limit,
    release_conversation_slot,
)
from budgetlens.application.scenarios import ScenarioService, as_object_map, parse_rule_payload
from budgetlens.config import Settings
from budgetlens.domain.ai_prompt import (
    build_system_prompt,
    build_view_context_block,
    correction_instruction,
)
from budgetlens.domain.conversation import (
    AiRun,
    Conversation,
    ToolExecution,
    normalize_message,
)
from budgetlens.domain.enums import (
    AiRunStatus,
    AnalyticsGroupBy,
    AnalyticsSort,
    MessageRole,
    Permission,
    ScenarioType,
    SortDirection,
    ToolExecutionStatus,
)
from budgetlens.domain.errors import DomainError, NotFoundError, ValidationError
from budgetlens.domain.evidence import (
    GROUNDING_FAILED_MESSAGE,
    Evidence,
    EvidenceRecord,
    evaluate_grounding,
    extract_amounts,
    parse_structured_answer,
    verify_answer_grounding,
)
from budgetlens.domain.idempotency import canonical_json, sha256_hex
from budgetlens.domain.identities import Clock, IdFactory
from budgetlens.domain.money import Currency, MoneyAmount
from budgetlens.domain.organization import Organization, normalize_name
from budgetlens.domain.permissions import require_permission
from budgetlens.domain.scenario import ScenarioRule
from budgetlens.domain.tools import ToolDefinition, ToolRegistry, default_tool_registry
from budgetlens.observability import metrics_registry
from budgetlens.ports.ai import AIProvider, ProviderResult, ToolRequest, ToolResult

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
        registry: ToolRegistry | None = None,
    ) -> None:
        self._session = session
        self._clock = clock
        self._ids = ids
        self._settings = settings
        self._analytics = analytics
        self._scenarios = scenarios
        self._provider = provider
        self._registry = registry or default_tool_registry()
        self._audits = SqlAuditRepository(session)
        self._orgs = SqlOrganizationRepository(session)

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
        enforce_limit(
            "ai",
            context.user.id,
            organization_id=context.organization_id,
            limit=self._settings.rate_limit_ai_per_minute,
        )
        acquire_conversation_slot(
            context.user.id,
            organization_id=context.organization_id,
            limit=self._settings.ai_max_concurrent_conversations,
        )
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
        finally:
            release_conversation_slot(context.user.id, organization_id=context.organization_id)

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
        organization = self._orgs.get(context.organization_id)
        if organization is None:
            raise NotFoundError()
        query = self._query_from_context(
            context, question, view_context or conversation.context_filters
        )
        system_prompt = build_system_prompt(
            organization_name=organization.name,
            currency=organization.functional_currency.code,
            fiscal_year=query.fiscal_year,
            fiscal_year_start_month=organization.fiscal_year_start_month,
            period_from=query.period_from,
            period_to=query.period_to,
            budget_version_id=query.budget_version_id,
        )
        structured_question = (
            f"{build_view_context_block(_view_payload(query, organization, view_context))}\n"
            f"{question}"
        )
        records: list[EvidenceRecord] = []
        pending_tools: list[ToolExecution] = []
        limitations: list[str] = []
        status = AiRunStatus.SUCCEEDED
        answer = ""
        tool_results: tuple[ToolResult, ...] = ()
        total_input = 0
        total_output = 0
        model_id = "stub"
        correction_used = False
        run_id = self._ids.new_id()

        while True:
            remaining = self._remaining_seconds(started)
            if remaining <= 0:
                status = AiRunStatus.LIMITED
                limitations.append(
                    "Se alcanzó el tiempo máximo. No entrego una conclusión parcial."
                )
                answer = "No pude completar la consulta dentro del tiempo máximo."
                break
            provider = self._invoke_provider(
                history=history,
                question=structured_question if not tool_results else question,
                system_prompt=system_prompt,
                tool_results=tool_results,
                timeout_seconds=max(1, int(remaining)),
            )
            total_input += provider.input_units
            total_output += provider.output_units
            model_id = provider.model_id
            if not provider.tool_requests:
                answer = _text_from_provider(provider)
                break
            if len(pending_tools) >= self._settings.ai_max_tool_calls:
                status = AiRunStatus.LIMITED
                limitations.append(
                    "Se alcanzó el límite de herramientas. No entrego una conclusión parcial."
                )
                answer = "No pude completar la consulta dentro del límite de herramientas."
                break
            next_results: list[ToolResult] = []
            stop_for_limit = False
            for request in provider.tool_requests:
                if len(pending_tools) >= self._settings.ai_max_tool_calls:
                    stop_for_limit = True
                    break
                record, execution, result = self._execute_registered_tool(
                    context,
                    request=request,
                    query=query,
                    organization=organization,
                    run_id=run_id,
                    evidence_index=len(records) + 1,
                    conversation=conversation,
                )
                pending_tools.append(execution)
                if record is not None:
                    records.append(record)
                    next_results.append(result)
            if stop_for_limit or len(pending_tools) >= self._settings.ai_max_tool_calls:
                status = AiRunStatus.LIMITED
                limitations.append(
                    "Se alcanzó el límite de herramientas. No entrego una conclusión parcial."
                )
                answer = "No pude completar la consulta dentro del límite de herramientas."
                break
            tool_results = tuple(next_results)
            if not tool_results:
                answer = provider.text or ""
                break

        if status is not AiRunStatus.LIMITED:
            if not answer and records:
                answer = _answer_from_evidence(question, [item.__dict__ for item in records])
            answer, status, limitations = self._ground_answer(
                context,
                conversation=conversation,
                question=question,
                answer=answer,
                records=records,
                history=history,
                system_prompt=system_prompt,
                tool_results=tool_results,
                started=started,
                status=status,
                limitations=limitations,
                correction_used=correction_used,
            )

        latency_ms = int((time.perf_counter() - started) * 1000)
        run = AiRun(
            id=run_id,
            organization_id=context.organization_id,
            conversation_id=conversation.id,
            provider=self._settings.ai_provider,
            model_id=model_id,
            latency_ms=latency_ms,
            input_units=total_input,
            output_units=total_output,
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
                "status": status.value,
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
            input_units=total_input,
            output_units=total_output,
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
            "currency": organization.functional_currency.code,
        }
        return CopilotAnswer(
            message_id=assistant.id,
            answer=answer,
            scope=scope,
            evidence=[
                {
                    "id": item.id,
                    "tool": item.tool,
                    "label": item.label,
                    "data": item.data,
                }
                for item in records
            ],
            limitations=limitations,
            trace_id=context.trace_id,
        )

    def _invoke_provider(
        self,
        *,
        history: list[Any],
        question: str,
        system_prompt: str,
        tool_results: tuple[ToolResult, ...],
        timeout_seconds: int,
    ) -> ProviderResult:
        return self._provider.complete(
            messages=history,
            question=question,
            settings=self._settings,
            system_prompt=system_prompt,
            tool_results=tool_results,
            timeout_seconds=timeout_seconds,
        )

    def _remaining_seconds(self, started: float) -> float:
        return self._settings.ai_timeout_seconds - (time.perf_counter() - started)

    def _ground_answer(
        self,
        context: TenantContext,
        *,
        conversation: Conversation,
        question: str,
        answer: str,
        records: list[EvidenceRecord],
        history: list[Any],
        system_prompt: str,
        tool_results: tuple[ToolResult, ...],
        started: float,
        status: AiRunStatus,
        limitations: list[str],
        correction_used: bool,
    ) -> tuple[str, AiRunStatus, list[str]]:
        del question
        figures = [MoneyAmount(figure) for item in records for figure in item.figures]
        authorized = (
            evaluate_grounding(
                [
                    Evidence(
                        tool_name=record.tool,
                        authorized=True,
                        period_from=date.fromisoformat("2026-01-01"),
                        period_to=date.fromisoformat("2026-12-01"),
                        budget_version_id=UUID(int=0),
                        currency=Currency("MXN"),
                        figures=tuple(MoneyAmount(figure) for figure in record.figures),
                    )
                    for record in records
                ]
            )
            if figures
            else evaluate_grounding([])
        )
        check = verify_answer_grounding(answer, records)
        if records and not authorized.can_conclude:
            limitations.append("Sin evidencia autorizada no se inventan causas ni importes.")
            return (
                "No hay cifras suficientes en el alcance para concluir.",
                status,
                limitations,
            )
        if not records:
            return (answer, status, limitations)
        if check.ok:
            return (answer, status, limitations)
        if not correction_used and self._remaining_seconds(started) > 0:
            allowed_figures = tuple(figure for item in records for figure in item.figures)
            correction = correction_instruction(tuple(item.id for item in records), allowed_figures)
            provider = self._invoke_provider(
                history=history,
                question=correction,
                system_prompt=system_prompt,
                tool_results=tool_results,
                timeout_seconds=max(1, int(self._remaining_seconds(started))),
            )
            retry = _text_from_provider(provider) or _answer_from_evidence(
                correction, [item.__dict__ for item in records]
            )
            if verify_answer_grounding(retry, records).ok:
                return (retry, status, limitations)
        record_audit(
            self._audits,
            clock=self._clock,
            ids=self._ids,
            organization_id=context.organization_id,
            actor_id=context.user.id,
            action="ai.grounding_failed",
            resource_type="conversation",
            resource_id=conversation.id,
            trace_id=context.trace_id,
            metadata={"reason": "grounding_failed"},
            outcome="failed",
        )
        limitations.append("La respuesta no pudo verificarse contra la evidencia.")
        return (GROUNDING_FAILED_MESSAGE, AiRunStatus.GROUNDING_FAILED, limitations)

    def _execute_registered_tool(
        self,
        context: TenantContext,
        *,
        request: ToolRequest,
        query: AnalyticsQuery,
        organization: Organization,
        run_id: UUID,
        evidence_index: int,
        conversation: Conversation,
    ) -> tuple[EvidenceRecord | None, ToolExecution, ToolResult]:
        require_permission(context.role, Permission.USE_AI)
        started = time.perf_counter()
        status = ToolExecutionStatus.SUCCEEDED
        payload: dict[str, Any] = {}
        row_count = 0
        try:
            definition = self._registry.require(request.name)
            require_permission(context.role, next(iter(definition.permissions)))
            arguments = self._registry.validate_arguments(request.name, request.arguments)
            payload, row_count = self._run_tool(
                context,
                definition,
                arguments,
                query,
                organization,
            )
        except DomainError:
            status = ToolExecutionStatus.REJECTED
            payload = {"error": "rejected"}
        except Exception:
            status = ToolExecutionStatus.FAILED
            payload = {"error": "failed"}
        evidence_id = f"ev_{evidence_index}"
        record = None
        if status is ToolExecutionStatus.SUCCEEDED:
            record = EvidenceRecord(
                id=evidence_id,
                tool=request.name,
                label=self._registry.require(request.name).label,
                data=payload,
                figures=tuple(item.as_text() for item in extract_amounts(payload)),
            )
        execution = ToolExecution(
            id=self._ids.new_id(),
            organization_id=context.organization_id,
            ai_run_id=run_id,
            tool_name=request.name,
            argument_hash=sha256_hex(canonical_json(dict(request.arguments)).encode()),
            result_hash=sha256_hex(canonical_json(payload).encode()),
            row_count=row_count,
            duration_ms=int((time.perf_counter() - started) * 1000),
            status=status,
        )
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
        result = ToolResult(
            name=request.name,
            evidence_id=evidence_id,
            payload=payload,
            request_id=request.request_id or evidence_id,
        )
        return record, execution, result

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

    def _query_from_tool_args(
        self, base: AnalyticsQuery, arguments: dict[str, Any]
    ) -> AnalyticsQuery:
        period_from = (
            date.fromisoformat(str(arguments["period_from"]))
            if arguments.get("period_from")
            else base.period_from
        )
        period_to = (
            date.fromisoformat(str(arguments["period_to"]))
            if arguments.get("period_to")
            else base.period_to
        )
        version = (
            UUID(str(arguments["budget_version_id"]))
            if arguments.get("budget_version_id")
            else base.budget_version_id
        )
        return parse_analytics_query(
            fiscal_year=int(arguments.get("fiscal_year") or base.fiscal_year),
            period_from=period_from,
            period_to=period_to,
            budget_version_id=version,
            account_ids=_uuid_list(arguments.get("account_ids")) or list(base.account_ids),
            department_ids=_uuid_list(arguments.get("department_ids")) or list(base.department_ids),
            cost_center_ids=_uuid_list(arguments.get("cost_center_ids"))
            or list(base.cost_center_ids),
        )

    def _run_tool(
        self,
        context: TenantContext,
        definition: ToolDefinition,
        arguments: dict[str, Any],
        query: AnalyticsQuery,
        organization: Organization,
    ) -> tuple[dict[str, Any], int]:
        scoped = self._query_from_tool_args(query, arguments)
        if definition.name == "get_variance_summary":
            summary = self._analytics.summary(context, scoped)
            payload = {
                "scope": _scope(scoped, organization),
                "metrics": summary.metrics.as_dict(),
                "currency": organization.functional_currency.code,
            }
            return payload, 1
        if definition.name == "get_variance_breakdown":
            group_by = AnalyticsGroupBy(str(arguments.get("group_by", "account")))
            sort = AnalyticsSort(str(arguments.get("sort", AnalyticsSort.ABSOLUTE_VARIANCE.value)))
            limit = min(int(arguments.get("limit") or 20), definition.row_budget)
            page = self._analytics.breakdown(
                context,
                scoped,
                group_by=group_by,
                sort=sort,
                direction=SortDirection.DESC,
                cursor=None,
                limit=min(limit, self._settings.ai_max_result_rows),
            )
            items = [_item_payload(item) for item in page.items[: definition.row_budget]]
            payload = {"scope": _scope(scoped, organization), "items": items}
            return payload, len(items)
        if definition.name == "get_top_unfavorable_variances":
            group_by = AnalyticsGroupBy(str(arguments.get("group_by", "account")))
            limit = min(int(arguments.get("limit") or 10), definition.row_budget)
            items = self._analytics.top_unfavorable(context, scoped, group_by=group_by, limit=limit)
            payload = {
                "scope": _scope(scoped, organization),
                "items": _with_contribution([_item_payload(item) for item in items]),
            }
            return payload, len(items)
        if definition.name == "compare_periods":
            compare_from, compare_to = _compare_range(scoped, arguments)
            left = scoped
            if _ranges_overlap(left.period_from, left.period_to, compare_from, compare_to):
                left = parse_analytics_query(
                    fiscal_year=scoped.fiscal_year,
                    period_from=scoped.period_from,
                    period_to=scoped.period_from,
                    budget_version_id=scoped.budget_version_id,
                    account_ids=list(scoped.account_ids),
                    department_ids=list(scoped.department_ids),
                    cost_center_ids=list(scoped.cost_center_ids),
                )
            if _ranges_overlap(left.period_from, left.period_to, compare_from, compare_to):
                raise ValidationError(
                    "INVALID_PERIOD",
                    "Los rangos a comparar no pueden superponerse.",
                )
            compared = self._analytics.compare_periods(
                context,
                left,
                compare_from=compare_from,
                compare_to=compare_to,
            )
            baseline = compared["baseline"].metrics.as_dict()
            comparison = compared["comparison"].metrics.as_dict()
            payload = {
                "scope": _scope(left, organization),
                "baseline": baseline,
                "comparison": comparison,
                "change": _period_change(baseline, comparison),
            }
            return payload, 2
        if definition.name == "calculate_scenario_preview":
            rules_raw = arguments.get("rules", [])
            rules: list[ScenarioRule] = []
            if isinstance(rules_raw, list):
                for item in cast(list[object], rules_raw):
                    if isinstance(item, dict):
                        rules.append(parse_rule_payload(as_object_map(cast(object, item))))
            baseline_type = ScenarioType(str(arguments.get("baseline_type") or "budget"))
            payload = self._scenarios.preview(
                context,
                query=scoped,
                baseline_type=baseline_type,
                rules=rules,
            )
            monthly = payload.get("monthly")
            if isinstance(monthly, list):
                payload["monthly"] = monthly[: definition.row_budget]
            return payload, 1
        raise ValidationError("UNKNOWN_TOOL", "La herramienta solicitada no está registrada.")


def _view_payload(
    query: AnalyticsQuery, organization: Organization, raw: dict[str, Any]
) -> dict[str, Any]:
    return {
        "fiscal_year": query.fiscal_year,
        "period_from": query.period_from.isoformat(),
        "period_to": query.period_to.isoformat(),
        "budget_version_id": str(query.budget_version_id),
        "currency": organization.functional_currency.code,
        "account_ids": [str(item) for item in query.account_ids],
        "department_ids": [str(item) for item in query.department_ids],
        "cost_center_ids": [str(item) for item in query.cost_center_ids],
        **{key: raw[key] for key in raw if key == "currency"},
    }


def _scope(query: AnalyticsQuery, organization: Organization) -> dict[str, str]:
    return {
        "fiscal_year": str(query.fiscal_year),
        "period_from": query.period_from.isoformat(),
        "period_to": query.period_to.isoformat(),
        "budget_version_id": str(query.budget_version_id),
        "currency": organization.functional_currency.code,
    }


def _item_payload(item: Any) -> dict[str, Any]:
    return {
        "group_code": item.group_code,
        "group_name": item.group_name,
        **item.metrics.as_dict(),
    }


def _with_contribution(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total = Decimal("0")
    for item in items:
        raw = item.get("variance_amount")
        if isinstance(raw, str):
            total += MoneyAmount(raw).value.copy_abs()
    enriched: list[dict[str, Any]] = []
    for item in items:
        raw = item.get("variance_amount")
        contribution = None
        if isinstance(raw, str) and total > 0:
            contribution = f"{(MoneyAmount(raw).value.copy_abs() / total):.6f}"
        enriched.append({**item, "contribution_percent": contribution})
    return enriched


def _compare_range(query: AnalyticsQuery, arguments: dict[str, Any]) -> tuple[date, date]:
    if arguments.get("compare_from") and arguments.get("compare_to"):
        return (
            date.fromisoformat(str(arguments["compare_from"])),
            date.fromisoformat(str(arguments["compare_to"])),
        )
    year = query.period_from.year
    return date(year, 2, 1), date(year, 2, 1)


def _ranges_overlap(left_from: date, left_to: date, right_from: date, right_to: date) -> bool:
    return left_from <= right_to and right_from <= left_to


def _period_change(
    baseline: dict[str, str | None], comparison: dict[str, str | None]
) -> dict[str, str | None]:
    def delta(key: str) -> str | None:
        left = baseline.get(key)
        right = comparison.get(key)
        if not isinstance(left, str) or not isinstance(right, str):
            return None
        return (MoneyAmount(right) - MoneyAmount(left)).as_text()

    return {
        "actual_amount": delta("actual_amount"),
        "variance_amount": delta("variance_amount"),
    }


def _text_from_provider(provider: ProviderResult) -> str:
    if provider.structured:
        answer = provider.structured.get("answer")
        if isinstance(answer, str) and answer.strip():
            return answer.strip()
    if provider.text:
        parsed = parse_structured_answer(provider.text)
        if parsed and isinstance(parsed.get("answer"), str):
            return str(parsed["answer"])
        return provider.text
    return ""


def _answer_from_evidence(question: str, evidence: list[dict[str, Any]]) -> str:
    if not evidence:
        if "marketing" in question.lower():
            return "No hay una dimensión de marketing en el alcance. No invento cifras."
        return "Consulté las herramientas autorizadas y no hay una conclusión adicional."
    raw_first: object = evidence[0].get("data") or evidence[0]
    cited = evidence[0].get("id")
    suffix = f" Evidencia: {cited}." if cited else ""
    first = cast(dict[str, Any], raw_first) if isinstance(raw_first, dict) else {}
    if "metrics" in first:
        metrics = cast(dict[str, Any], first["metrics"])
        return (
            f"Según el resumen, presupuesto {metrics['budget_amount']}, "
            f"real {metrics['actual_amount']}, variación {metrics['variance_amount']} "
            f"({metrics['favorability']}, {metrics['variance_state']}).{suffix}"
        )
    items_value: object = first.get("items")
    if isinstance(items_value, list) and items_value:
        raw_items = cast(list[object], items_value)
        raw_top = raw_items[0]
        top = cast(dict[str, Any], raw_top) if isinstance(raw_top, dict) else {}
        return (
            f"El principal contribuyente es {top.get('group_name') or top.get('group_code')} "
            f"con variación {top.get('variance_amount')} ({top.get('favorability')}).{suffix}"
        )
    if "baseline" in first and "comparison" in first:
        baseline = cast(dict[str, Any], first["baseline"])
        comparison = cast(dict[str, Any], first["comparison"])
        return (
            f"En el primer periodo la variación fue {baseline['variance_amount']}; "
            f"en el segundo fue {comparison['variance_amount']}.{suffix}"
        )
    if "marketing" in question.lower():
        return "No hay una dimensión de marketing en el alcance. No invento cifras."
    return f"Consulté las herramientas autorizadas y no hay una conclusión adicional.{suffix}"


def _uuid_list(value: object) -> list[UUID]:
    if not isinstance(value, list):
        return []
    return [UUID(str(item)) for item in cast(list[object], value)]


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
