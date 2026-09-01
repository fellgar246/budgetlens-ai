from __future__ import annotations

import importlib
from typing import Any, Protocol, cast

from budgetlens.config import Settings
from budgetlens.domain.conversation import ConversationMessage
from budgetlens.domain.errors import ai_unavailable
from budgetlens.ports.ai import AIProvider, ProviderResult, ToolRequest


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

TOOL_SPECS: tuple[dict[str, Any], ...] = (
    {
        "toolSpec": {
            "name": "get_variance_summary",
            "description": "Return authorized budget, actual, and variance totals.",
            "inputSchema": {"json": {"type": "object", "properties": {}}},
        }
    },
    {
        "toolSpec": {
            "name": "get_variance_breakdown",
            "description": "Return an aggregated variance breakdown.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "group_by": {
                            "type": "string",
                            "enum": ["account", "department", "cost_center", "period"],
                        }
                    },
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "get_top_unfavorable_variances",
            "description": "Return the largest unfavorable variances.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "group_by": {
                            "type": "string",
                            "enum": ["account", "department", "cost_center", "period"],
                        }
                    },
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "compare_periods",
            "description": "Compare two authorized period ranges.",
            "inputSchema": {"json": {"type": "object", "properties": {}}},
        }
    },
    {
        "toolSpec": {
            "name": "calculate_scenario_preview",
            "description": "Preview scenario rules without saving.",
            "inputSchema": {"json": {"type": "object", "properties": {}}},
        }
    },
)


class DeterministicAIProvider:
    def complete(
        self,
        *,
        messages: list[ConversationMessage],
        question: str,
        settings: Settings,
    ) -> ProviderResult:
        del messages
        text = question.lower()
        if "loop infinito" in text or "solicita tools indefinidamente" in text:
            return ProviderResult(
                text=None,
                tool_requests=tuple(
                    ToolRequest("get_variance_summary", {})
                    for _ in range(settings.ai_max_tool_calls + 3)
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
        if any(
            marker in text
            for marker in ("clima", "receta", "system prompt", "instrucciones internas")
        ):
            return ProviderResult(
                text="Esa solicitud está fuera del dominio de análisis presupuestario.",
                tool_requests=(),
                input_units=3,
                output_units=8,
                model_id="stub",
            )
        if "entre enero y febrero" in text or "enero y febrero" in text:
            return ProviderResult(
                text=None,
                tool_requests=(ToolRequest("compare_periods", {"group": "period"}),),
                input_units=6,
                output_units=4,
                model_id="stub",
            )
        if "mayor desviación" in text or "desfavorable" in text and "febrero" in text:
            return ProviderResult(
                text=None,
                tool_requests=(
                    ToolRequest("get_top_unfavorable_variances", {"group_by": "account"}),
                ),
                input_units=6,
                output_units=4,
                model_id="stub",
            )
        if "departamento" in text or "explicó" in text or "explico" in text or "exceso" in text:
            group = "department" if "departamento" in text else "account"
            return ProviderResult(
                text=None,
                tool_requests=(ToolRequest("get_variance_breakdown", {"group_by": group}),),
                input_units=6,
                output_units=4,
                model_id="stub",
            )
        return ProviderResult(
            text=None,
            tool_requests=(ToolRequest("get_variance_summary", {}),),
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
    ) -> ProviderResult:
        del settings
        payload_messages = _to_bedrock_messages(messages, question)
        try:
            raw = self._require_client().converse(
                modelId=self._model_id,
                messages=payload_messages,
                toolConfig={"tools": list(TOOL_SPECS)},
            )
        except Exception as exc:
            raise ai_unavailable() from exc
        return _from_bedrock_response(raw, model_id=self._model_id)


def _to_bedrock_messages(
    messages: list[ConversationMessage], question: str
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
            if name:
                tools.append(ToolRequest(name=name, arguments=arguments))
    usage = _as_object_map(response.get("usage"))
    input_units = int(usage.get("inputTokens") or 0) if usage else 0
    output_units = int(usage.get("outputTokens") or 0) if usage else 0
    return ProviderResult(
        text="\n".join(texts) if texts else None,
        tool_requests=tuple(tools),
        input_units=input_units,
        output_units=output_units,
        model_id=model_id or "bedrock",
    )


def _load_bedrock_client(region: str, timeout_seconds: int) -> _ConverseClient:
    del timeout_seconds
    return cast(_ConverseClient, _boto3_client("bedrock-runtime", region_name=region))


def _boto3_client(service: str, **kwargs: object) -> object:
    try:
        module = importlib.import_module("boto3")
    except ImportError as exc:
        raise ai_unavailable() from exc
    factory = getattr(module, "client", None)
    if not callable(factory):
        raise ai_unavailable()
    return factory(service, **kwargs)


def build_ai_provider_from_settings(settings: Settings, *, client: Any | None = None) -> AIProvider:
    if settings.ai_provider == "bedrock":
        return BedrockAIProvider(
            region=settings.bedrock_region,
            model_id=settings.bedrock_model_id,
            timeout_seconds=settings.ai_timeout_seconds,
            client=client,
        )
    return DeterministicAIProvider()
