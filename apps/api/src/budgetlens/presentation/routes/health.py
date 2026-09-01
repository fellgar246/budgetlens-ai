from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Response
from pydantic import BaseModel, ConfigDict

from budgetlens.adapters.db import ping_database
from budgetlens.config import get_settings

router = APIRouter(tags=["system"])


class LiveResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ok"]


class ReadyComponents(BaseModel):
    model_config = ConfigDict(extra="forbid")
    database: Literal["ok", "error"]


class ReadyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ready", "unavailable"]
    components: ReadyComponents


class VersionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    commit: str
    build_time: str


@router.get("/health/live", response_model=LiveResponse, operation_id="get_health_live")
def live() -> LiveResponse:
    return LiveResponse(status="ok")


@router.get(
    "/health/ready",
    response_model=ReadyResponse,
    responses={503: {"model": ReadyResponse}},
    operation_id="get_health_ready",
)
def ready(response: Response) -> ReadyResponse:
    database_ok = ping_database()
    payload = ReadyResponse(
        status="ready" if database_ok else "unavailable",
        components=ReadyComponents(database="ok" if database_ok else "error"),
    )
    if not database_ok:
        response.status_code = 503
    return payload


@router.get("/version", response_model=VersionResponse, operation_id="get_version")
def version() -> VersionResponse:
    settings = get_settings()
    return VersionResponse(
        version=settings.app_version,
        commit=settings.git_sha,
        build_time=settings.build_time,
    )
