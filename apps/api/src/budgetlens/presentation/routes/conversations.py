from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from budgetlens.presentation.deps import ConversationServiceDep, CurrentTenant
from budgetlens.presentation.schemas import PageInfo
from budgetlens.presentation.schemas_ops import (
    ConversationListResponse,
    ConversationResponse,
    CopilotMessageResponse,
    CreateConversationRequest,
    CreateMessageRequest,
    conversation_response,
    copilot_response,
)

router = APIRouter(tags=["conversations"])


@router.get(
    "/conversations", response_model=ConversationListResponse, operation_id="list_conversations"
)
def list_conversations(
    context: CurrentTenant,
    service: ConversationServiceDep,
    cursor: str | None = None,
    limit: int | None = Query(default=None, ge=1, le=100),
) -> ConversationListResponse:
    page = service.list(context, cursor=cursor, limit=limit)
    return ConversationListResponse(
        items=[conversation_response(item) for item in page.items],
        page=PageInfo(next_cursor=page.next_cursor, has_more=page.has_more),
    )


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=201,
    operation_id="create_conversation",
)
def create_conversation(
    payload: CreateConversationRequest,
    context: CurrentTenant,
    service: ConversationServiceDep,
) -> ConversationResponse:
    return conversation_response(
        service.create(context, title=payload.title, filters=payload.context)
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    operation_id="get_conversation",
)
def get_conversation(
    conversation_id: UUID, context: CurrentTenant, service: ConversationServiceDep
) -> ConversationResponse:
    return conversation_response(service.get(context, conversation_id))


@router.delete(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    operation_id="delete_conversation",
)
def delete_conversation(
    conversation_id: UUID, context: CurrentTenant, service: ConversationServiceDep
) -> ConversationResponse:
    return conversation_response(service.delete(context, conversation_id))


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=CopilotMessageResponse,
    operation_id="create_conversation_message",
)
def create_conversation_message(
    conversation_id: UUID,
    payload: CreateMessageRequest,
    context: CurrentTenant,
    service: ConversationServiceDep,
) -> CopilotMessageResponse:
    return copilot_response(
        service.ask(
            context,
            conversation_id=conversation_id,
            content=payload.content,
            view_context=payload.context,
        )
    )
