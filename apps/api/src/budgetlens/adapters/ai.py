from __future__ import annotations

import importlib
from typing import Any, Protocol, cast

from budgetlens.config import Settings
from budgetlens.domain.conversation import ConversationMessage
from budgetlens.domain.errors import ai_unavailable
from budgetlens.domain.tools import default_tool_registry
from budgetlens.ports.ai import AIProvider, ProviderResult, ToolRequest, ToolResult

TOOL_REGISTRY = default_tool_registry()
TOOL_SPECS: tuple[dict[str, Any], ...] = TOOL_REGISTRY.bedrock_specs()


class _ConverseClient(Protocol):
    def converse(self, **kwargs: Any) -> dict[str, Any]: ...


MUTATION_MARKERS = (
    "cambia",
    "cambiar",
    "actualiza",
    "borra",
    "elimina",
    "publica",
    "importa",
    "guarda el presupuesto",
    "ejecuta sql",
    "run_query",
    "execute_sql",
)
OUT_OF_DOMAIN = ("clima", "receta", "roi", "sql", "system prompt", "instrucciones internas")


class DeterministicAIProvider:
    def complete(
        self,
        *,
        messages: list[ConversationMessage],
        question: str,
        settings: Settings,
        system_prompt: str = "",
        tool_results: tuple[ToolResult, ...] = (),
        timeout_seconds: int | None = None,
    ) -> ProviderResult:
        del messages, system_prompt, timeout_seconds
        text = question.lower()
        looping = "loop infinito" in text or "solicita tools indefinidamente" in text
        if tool_results and not looping:
            return _result_from_tool_results(tool_results)
        if looping:
            return ProviderResult(
                text=None,
                tool_requests=tuple(
                    ToolRequest("get_variance_summary", {}, request_id=f"call_{index}")
                    for index in range(settings.ai_max_tool_calls + 3)
                ),
                input_units=8,
                output_units=8,
                model_id="stub",
            )
        if any(marker in text for marker in MUTATION_MARKERS):
            return ProviderResult(
                text=(
                    "No puedo modificar presupuesto, importar ni ejecutar acciones. "
                    "Solo consulto cifras ya calculadas."
                ),
                tool_requests=(),
                input_units=4,
                output_units=12,
                model_id="stub",
            )
        if "beta" in text and (
            "organización" in text or "organizacion" in text or "muéstrame" in text
        ):
            return ProviderResult(
                text="Solo puedo consultar la organización activa. No tengo acceso a otra empresa.",
                tool_requests=(),
                input_units=4,
                output_units=10,
                model_id="stub",
            )
        if "roi" in text:
            return ProviderResult(
                text="No puedo calcular un ROI sin inversión y retorno definidos en el alcance.",
                tool_requests=(),
                input_units=3,
                output_units=8,
                model_id="stub",
            )
        if any(marker in text for marker in OUT_OF_DOMAIN):
            return ProviderResult(
                text="Esa solicitud está fuera del dominio de análisis presupuestario.",
                tool_requests=(),
                input_units=3,
                output_units=8,
                model_id="stub",
            )
        if "está bien el negocio" in text or "esta bien el negocio" in text:
            return ProviderResult(
                text=(
                    "Necesito una métrica y un alcance. "
                    "No concluyo la salud del negocio sin cifras."
                ),
                tool_requests=(),
                input_units=3,
                output_units=8,
                model_id="stub",
            )
        if "marketing" in text:
            return ProviderResult(
                text="No hay una dimensión de marketing en el alcance. No invento cifras.",
                tool_requests=(),
                input_units=3,
                output_units=8,
                model_id="stub",
            )
        if "analiza 2025" in text:
            return ProviderResult(
                text="No hay datos de 2025 en el alcance autorizado. No invento cifras.",
                tool_requests=(),
                input_units=3,
                output_units=8,
                model_id="stub",
            )
        if "desglosa" in text or "desglose" in text:
            return ProviderResult(
                text=None,
                tool_requests=(
                    ToolRequest(
                        "get_variance_breakdown",
                        {"group_by": "account", "limit": 20},
                        request_id="call_breakdown",
                    ),
                ),
                input_units=6,
                output_units=4,
                model_id="stub",
            )
        if "100.000 filas" in text or "100,000 filas" in text or "100000 filas" in text:
            return ProviderResult(
                text=None,
                tool_requests=(
                    ToolRequest(
                        "get_variance_breakdown",
                        {"group_by": "account", "limit": 20},
                        request_id="call_limit",
                    ),
                ),
                input_units=6,
                output_units=4,
                model_id="stub",
            )
        if "entre enero y febrero" in text or "enero y febrero" in text:
            return ProviderResult(
                text=None,
                tool_requests=(
                    ToolRequest(
                        "compare_periods",
                        {"compare_from": "2026-02-01", "compare_to": "2026-02-01"},
                        request_id="call_compare",
                    ),
                ),
                input_units=6,
                output_units=4,
                model_id="stub",
            )
        if "mayor desviación" in text or ("desfavorable" in text and "febrero" in text):
            return ProviderResult(
                text=None,
                tool_requests=(
                    ToolRequest(
                        "get_top_unfavorable_variances",
                        {"group_by": "account", "limit": 10},
                        request_id="call_top",
                    ),
                ),
                input_units=6,
                output_units=4,
                model_id="stub",
            )
        if "departamento" in text or "explicó" in text or "explico" in text or "exceso" in text:
            group = "department" if "departamento" in text else "account"
            return ProviderResult(
                text=None,
                tool_requests=(
                    ToolRequest(
                        "get_variance_breakdown",
                        {"group_by": group, "limit": 20},
                        request_id="call_breakdown",
                    ),
                ),
                input_units=6,
                output_units=4,
                model_id="stub",
            )
        return ProviderResult(
            text=None,
            tool_requests=(ToolRequest("get_variance_summary", {}, request_id="call_summary"),),
            input_units=5,
            output_units=3,
            model_id="stub",
        )


class BedrockAIProvider:
    def __init__(
        self,
        *,
        region: str,
        model_id: str,
        timeout_seconds: int,
        client: Any | None = None,
    ) -> None:
        self._region = region
        self._model_id = model_id.strip()
        self._timeout_seconds = timeout_seconds
        self._client = client

    def _require_client(self) -> _ConverseClient:
        if self._client is not None:
            return cast(_ConverseClient, self._client)
        if not self._model_id:
            raise ai_unavailable()
        self._client = _load_bedrock_client(self._region, self._timeout_seconds)
        return self._client

    def complete(
        self,
        *,
        messages: list[ConversationMessage],
        question: str,
        settings: Settings,
        system_prompt: str = "",
        tool_results: tuple[ToolResult, ...] = (),
        timeout_seconds: int | None = None,
    ) -> ProviderResult:
        del settings
        payload_messages = _to_bedrock_messages(messages, question, tool_results)
        timeout = timeout_seconds if timeout_seconds is not None else self._timeout_seconds
        try:
            raw = self._require_client().converse(
                modelId=self._model_id,
                messages=payload_messages,
                system=[{"text": system_prompt}] if system_prompt else [],
                toolConfig={"tools": list(TOOL_SPECS)},
                inferenceConfig={"maxTokens": 1024},
                additionalModelRequestFields=_structured_output_hint(),
                requestTimeout=timeout,
            )
        except TypeError:
            try:
                raw = self._require_client().converse(
                    modelId=self._model_id,
                    messages=payload_messages,
                    system=[{"text": system_prompt}] if system_prompt else [],
                    toolConfig={"tools": list(TOOL_SPECS)},
                )
            except Exception as exc:
                raise ai_unavailable() from exc
        except Exception as exc:
            raise ai_unavailable() from exc
        return _from_bedrock_response(raw, model_id=self._model_id)


def _structured_output_hint() -> dict[str, Any]:
    return {}


def _result_from_tool_results(tool_results: tuple[ToolResult, ...]) -> ProviderResult:
    first = tool_results[0].payload if tool_results else {}
    cited = [item.evidence_id for item in tool_results if item.evidence_id]
    text = _answer_from_payload(first, cited)
    return ProviderResult(
        text=text,
        tool_requests=(),
        input_units=4,
        output_units=10,
        model_id="stub",
        structured={"answer": text, "cited_evidence": cited, "limitations": []},
    )


def _answer_from_payload(payload: dict[str, Any], cited: list[str]) -> str:
    if payload.get("error"):
        return (
            "No pude completar la consulta por un error interno. "
            "Identificador de seguimiento: eval-trace."
        )
    citation = f" Evidencia: {', '.join(cited)}." if cited else ""
    if "metrics" in payload and isinstance(payload["metrics"], dict):
        metrics = cast(dict[str, Any], payload["metrics"])
        return (
            f"Según el resumen, presupuesto {metrics.get('budget_amount')}, "
            f"real {metrics.get('actual_amount')}, variación {metrics.get('variance_amount')} "
            f"({metrics.get('favorability')}, {metrics.get('variance_state')}).{citation}"
        )
    items = payload.get("items")
    if isinstance(items, list) and items:
        typed_items = cast(list[object], items)
        raw_top = typed_items[0]
        if isinstance(raw_top, dict):
            top = cast(dict[str, Any], raw_top)
            return (
                f"El principal contribuyente es {top.get('group_name') or top.get('group_code')} "
                f"con variación {top.get('variance_amount')} ({top.get('favorability')}).{citation}"
            )
    if "baseline" in payload and "comparison" in payload:
        raw_baseline = payload["baseline"]
        raw_comparison = payload["comparison"]
        if isinstance(raw_baseline, dict) and isinstance(raw_comparison, dict):
            baseline = cast(dict[str, Any], raw_baseline)
            comparison = cast(dict[str, Any], raw_comparison)
            return (
                f"En el primer periodo la variación fue {baseline.get('variance_amount')}; "
                f"en el segundo fue {comparison.get('variance_amount')}.{citation}"
            )
    return f"Consulté las herramientas autorizadas y no hay una conclusión adicional.{citation}"


def _to_bedrock_messages(
    messages: list[ConversationMessage],
    question: str,
    tool_results: tuple[ToolResult, ...],
) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for item in messages:
        payload.append(
            {
                "role": "user" if item.role.value == "user" else "assistant",
                "content": [{"text": item.content}],
            }
        )
    if not payload or payload[-1]["role"] != "user":
        payload.append({"role": "user", "content": [{"text": question}]})
    if tool_results:
        payload.append(
            {
                "role": "user",
                "content": [
                    {
                        "toolResult": {
                            "toolUseId": item.request_id or item.evidence_id,
                            "content": [{"json": item.payload}],
                        }
                    }
                    for item in tool_results
                ],
            }
        )
    return payload


def _as_object_map(value: object) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return cast(dict[str, Any], value)


def _from_bedrock_response(response: dict[str, Any], *, model_id: str) -> ProviderResult:
    output = _as_object_map(response.get("output"))
    message = _as_object_map(output.get("message") if output else None)
    content = message.get("content") if message else None
    texts: list[str] = []
    tools: list[ToolRequest] = []
    if isinstance(content, list):
        for raw_block in cast(list[object], content):
            block = _as_object_map(raw_block)
            if block is None:
                continue
            text = block.get("text")
            if isinstance(text, str) and text.strip():
                texts.append(text.strip())
            tool_use = _as_object_map(block.get("toolUse"))
            if tool_use is None:
                continue
            name = str(tool_use.get("name") or "")
            raw_args = _as_object_map(tool_use.get("input")) or {}
            arguments = {str(key): item for key, item in raw_args.items()}
            request_id = str(tool_use.get("toolUseId") or name)
            if name:
                tools.append(ToolRequest(name=name, arguments=arguments, request_id=request_id))
    usage = _as_object_map(response.get("usage"))
    input_units = int(usage.get("inputTokens") or 0) if usage else 0
    output_units = int(usage.get("outputTokens") or 0) if usage else 0
    joined = "\n".join(texts) if texts else None
    structured = None
    if joined:
        from budgetlens.domain.evidence import parse_structured_answer

        structured = parse_structured_answer(joined)
    return ProviderResult(
        text=joined,
        tool_requests=tuple(tools),
        input_units=input_units,
        output_units=output_units,
        model_id=model_id or "bedrock",
        structured=structured,
    )


def _load_bedrock_client(region: str, timeout_seconds: int) -> _ConverseClient:
    return cast(
        _ConverseClient,
        _boto3_client(
            "bedrock-runtime",
            region_name=region,
            config=_botocore_config(timeout_seconds),
        ),
    )


def _botocore_config(timeout_seconds: int) -> object | None:
    try:
        module = importlib.import_module("botocore.config")
    except ImportError:
        return None
    factory = getattr(module, "Config", None)
    if not callable(factory):
        return None
    return factory(
        read_timeout=timeout_seconds,
        connect_timeout=min(3, timeout_seconds),
        retries={"max_attempts": 1},
    )


def _boto3_client(service: str, **kwargs: object) -> object:
    try:
        module = importlib.import_module("boto3")
    except ImportError as exc:
        raise ai_unavailable() from exc
    factory = getattr(module, "client", None)
    if not callable(factory):
        raise ai_unavailable()
    cleaned = {key: value for key, value in kwargs.items() if value is not None}
    return factory(service, **cleaned)


def build_ai_provider_from_settings(settings: Settings, *, client: Any | None = None) -> AIProvider:
    if settings.ai_provider == "bedrock":
        return BedrockAIProvider(
            region=settings.bedrock_region,
            model_id=settings.bedrock_model_id,
            timeout_seconds=settings.ai_timeout_seconds,
            client=client,
        )
    return DeterministicAIProvider()
