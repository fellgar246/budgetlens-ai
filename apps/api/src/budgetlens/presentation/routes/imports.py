from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from budgetlens.domain.enums import ScenarioType
from budgetlens.presentation.deps import CurrentTenant, ImportServiceDep
from budgetlens.presentation.headers import RequiredIdempotencyKey
from budgetlens.presentation.schemas import PageInfo
from budgetlens.presentation.schemas_ops import (
    CreateImportRequest,
    ImportErrorListResponse,
    ImportJobListResponse,
    ImportJobResponse,
    ImportPreviewResponse,
    ImportUploadInfo,
    ValidateImportRequest,
    import_error_group,
    import_error_item,
    import_job_response,
)

router = APIRouter(tags=["imports"])


@router.get("/imports", response_model=ImportJobListResponse, operation_id="list_imports")
def list_imports(
    context: CurrentTenant,
    service: ImportServiceDep,
    cursor: str | None = None,
    limit: int | None = Query(default=None, ge=1, le=100),
) -> ImportJobListResponse:
    page = service.list(context, cursor=cursor, limit=limit)
    return ImportJobListResponse(
        items=[import_job_response(item) for item in page.items],
        page=PageInfo(next_cursor=page.next_cursor, has_more=page.has_more),
    )


@router.post(
    "/imports", response_model=ImportJobResponse, status_code=201, operation_id="create_import"
)
def create_import(
    payload: CreateImportRequest,
    context: CurrentTenant,
    service: ImportServiceDep,
) -> ImportJobResponse:
    job = service.create(
        context,
        import_type=ScenarioType(payload.import_type),
        budget_version_id=payload.budget_version_id,
        original_filename=payload.original_filename,
        size_bytes=payload.size_bytes,
        sha256=payload.sha256,
        template_version=payload.template_version,
    )
    target = service.upload_descriptor(context, job)
    return import_job_response(
        job,
        upload=ImportUploadInfo(mode=target.mode, method=target.method, url=target.url),
    )


@router.put(
    "/imports/{job_id}/content",
    response_model=ImportJobResponse,
    operation_id="upload_import_content",
)
async def upload_import_content(
    job_id: UUID,
    request: Request,
    context: CurrentTenant,
    service: ImportServiceDep,
) -> ImportJobResponse:
    content = await request.body()
    return import_job_response(
        service.upload_content(
            context,
            job_id=job_id,
            content=content,
            media_type=request.headers.get("content-type"),
        )
    )


@router.post(
    "/imports/{job_id}/validate", response_model=ImportJobResponse, operation_id="validate_import"
)
def validate_import(
    job_id: UUID,
    payload: ValidateImportRequest,
    context: CurrentTenant,
    service: ImportServiceDep,
) -> ImportJobResponse:
    return import_job_response(
        service.validate(
            context,
            job_id=job_id,
            mapping=payload.mapping,
            create_missing_dimensions=payload.create_missing_dimensions,
            amount_locale=payload.amount_locale,
            sheet_name=payload.sheet_name,
            delimiter=payload.delimiter,
        )
    )


@router.get("/imports/{job_id}", response_model=ImportJobResponse, operation_id="get_import")
def get_import(
    job_id: UUID, context: CurrentTenant, service: ImportServiceDep
) -> ImportJobResponse:
    return import_job_response(service.get(context, job_id))


@router.get(
    "/imports/{job_id}/preview", response_model=ImportPreviewResponse, operation_id="preview_import"
)
def preview_import(
    job_id: UUID,
    context: CurrentTenant,
    service: ImportServiceDep,
    cursor: str | None = None,
    limit: int | None = Query(default=None, ge=1, le=50),
) -> ImportPreviewResponse:
    preview = service.preview(context, job_id=job_id, cursor=cursor, limit=limit)
    return ImportPreviewResponse(
        job=import_job_response(preview.job),
        headers=preview.headers,
        proposed_mapping=preview.proposed_mapping,
        items=preview.rows,
        new_accounts=preview.new_accounts,
        new_departments=preview.new_departments,
        new_cost_centers=preview.new_cost_centers,
        replaced_records=preview.replaced_records,
        sha256_short=preview.sha256_short,
        delimiter=preview.delimiter,
        delimiter_ambiguous=preview.delimiter_ambiguous,
        available_sheets=preview.available_sheets,
        error_groups=[import_error_group(group) for group in preview.error_groups],
        page=PageInfo(next_cursor=preview.next_cursor, has_more=preview.has_more),
    )


@router.get(
    "/imports/{job_id}/errors",
    response_model=ImportErrorListResponse,
    operation_id="list_import_errors",
)
def list_import_errors(
    job_id: UUID,
    context: CurrentTenant,
    service: ImportServiceDep,
    cursor: str | None = None,
    limit: int | None = Query(default=None, ge=1, le=100),
) -> ImportErrorListResponse:
    page = service.list_errors(context, job_id=job_id, cursor=cursor, limit=limit)
    return ImportErrorListResponse(
        items=[import_error_item(item) for item in page.items],
        page=PageInfo(next_cursor=page.next_cursor, has_more=page.has_more),
    )


@router.get("/imports/{job_id}/error-report", operation_id="download_import_errors")
def download_import_errors(
    job_id: UUID, context: CurrentTenant, service: ImportServiceDep
) -> Response:
    content = service.error_report(context, job_id=job_id)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="budgetlens-import-errors-{job_id}.csv"'
        },
    )


@router.post(
    "/imports/{job_id}/commit", response_model=ImportJobResponse, operation_id="commit_import"
)
def commit_import(
    job_id: UUID,
    context: CurrentTenant,
    service: ImportServiceDep,
    idempotency_key: RequiredIdempotencyKey,
) -> ImportJobResponse:
    return import_job_response(
        service.commit(context, job_id=job_id, idempotency_key=idempotency_key)
    )


@router.post(
    "/imports/{job_id}/cancel", response_model=ImportJobResponse, operation_id="cancel_import"
)
def cancel_import(
    job_id: UUID, context: CurrentTenant, service: ImportServiceDep
) -> ImportJobResponse:
    return import_job_response(service.cancel(context, job_id=job_id))
