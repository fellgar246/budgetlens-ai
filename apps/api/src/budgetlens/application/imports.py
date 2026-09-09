from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from budgetlens.adapters.persistence.finance_repositories import (
    SqlFinancialEntryRepository,
    SqlImportErrorRepository,
    SqlImportJobRepository,
)
from budgetlens.adapters.persistence.repositories import (
    SqlAccountRepository,
    SqlAuditRepository,
    SqlBudgetVersionRepository,
    SqlCostCenterRepository,
    SqlDepartmentRepository,
    SqlOrganizationRepository,
)
from budgetlens.application.audit import record_audit
from budgetlens.application.context import TenantContext
from budgetlens.application.idempotency_keys import (
    hash_payload,
    replay_or_reserve,
    require_idempotency_key,
)
from budgetlens.application.pagination import (
    Page,
    clamp_limit,
    clamp_preview_limit,
    decode_cursor,
    encode_cursor,
)
from budgetlens.application.rate_limit import enforce_limit
from budgetlens.application.row_normalization import normalize_row
from budgetlens.config import Settings
from budgetlens.domain.audit import (
    IMPORT_CANCELLED,
    IMPORT_COMMITTED,
    IMPORT_CREATED,
    IMPORT_FAILED,
    IMPORT_VALIDATED,
)
from budgetlens.domain.budget_version import BudgetVersion
from budgetlens.domain.dimensions import Account, CostCenter, Department, normalize_code
from budgetlens.domain.enums import (
    UNASSIGNED_CODE,
    AccountType,
    DimensionStatus,
    ImportErrorSeverity,
    ImportJobStatus,
    Permission,
    Role,
    ScenarioType,
)
from budgetlens.domain.errors import (
    ConflictError,
    DomainError,
    NotFoundError,
    PayloadTooLargeError,
    ValidationError,
    field_issue,
)
from budgetlens.domain.exporting import render_csv
from budgetlens.domain.financial_entry import FinancialEntry
from budgetlens.domain.idempotency import sha256_hex
from budgetlens.domain.identities import Clock, IdFactory
from budgetlens.domain.importing import (
    ImportErrorGroup,
    ImportIssue,
    ImportJob,
    NormalizedImportRow,
    ParsedCellRow,
    WorkbookTable,
    abbreviated_sha256,
    group_import_issues,
    propose_mapping,
    validate_mapping,
)
from budgetlens.domain.organization import Organization, normalize_name
from budgetlens.domain.permissions import can_create_missing_dimensions, require_permission
from budgetlens.domain.text_safety import redact_cell, sanitize_filename
from budgetlens.observability import metrics_registry
from budgetlens.ports.imports import ImportExecutor
from budgetlens.ports.parsing import WorkbookParser
from budgetlens.ports.storage import ObjectStorage


@dataclass(frozen=True, slots=True)
class UploadTarget:
    mode: str
    method: str
    url: str


@dataclass(frozen=True, slots=True)
class ImportPreview:
    job: ImportJob
    headers: list[str]
    proposed_mapping: dict[str, str]
    rows: list[dict[str, str]]
    new_accounts: int
    new_departments: int
    new_cost_centers: int
    replaced_records: int
    sha256_short: str
    delimiter: str | None
    delimiter_ambiguous: bool
    available_sheets: list[str]
    error_groups: list[ImportErrorGroup]
    next_cursor: str | None
    has_more: bool


class ImportService:
    def __init__(
        self,
        session: Session,
        clock: Clock,
        ids: IdFactory,
        storage: ObjectStorage,
        settings: Settings,
        executor: ImportExecutor,
        parser: WorkbookParser,
    ) -> None:
        self._session = session
        self._clock = clock
        self._ids = ids
        self._storage = storage
        self._settings = settings
        self._executor = executor
        self._parser = parser
        self._orgs = SqlOrganizationRepository(session)
        self._audits = SqlAuditRepository(session)

    def _jobs(self, organization_id: UUID) -> SqlImportJobRepository:
        return SqlImportJobRepository(self._session, organization_id)

    def _errors(self, organization_id: UUID) -> SqlImportErrorRepository:
        return SqlImportErrorRepository(self._session, organization_id)

    def list(
        self, context: TenantContext, *, cursor: str | None, limit: int | None
    ) -> Page[ImportJob]:
        return self._jobs(context.organization_id).list_page(
            cursor=cursor, limit=clamp_limit(limit)
        )

    def get(self, context: TenantContext, job_id: UUID) -> ImportJob:
        job = self._jobs(context.organization_id).get(job_id)
        if job is None:
            raise NotFoundError()
        return job

    def create(
        self,
        context: TenantContext,
        *,
        import_type: ScenarioType,
        budget_version_id: UUID | None,
        original_filename: str,
        size_bytes: int,
        sha256: str,
        template_version: str,
    ) -> ImportJob:
        require_permission(context.role, Permission.IMPORT)
        if size_bytes > self._settings.max_upload_bytes:
            raise PayloadTooLargeError()
        if len(sha256) != 64 or any(char not in "0123456789abcdefABCDEF" for char in sha256):
            raise ValidationError("UNSUPPORTED_FILE", "La huella del archivo no es válida.")
        filename = sanitize_filename(original_filename)
        if filename == "upload.bin" and not Path(original_filename).name.strip():
            raise ValidationError("UNSUPPORTED_FILE", "El nombre de archivo no es válido.")
        organization = self._require_org(context.organization_id)
        version = self._require_version_for_create(
            context, import_type=import_type, budget_version_id=budget_version_id
        )
        del organization, version
        job = ImportJob(
            id=self._ids.new_id(),
            organization_id=context.organization_id,
            created_by=context.user.id,
            import_type=import_type,
            budget_version_id=budget_version_id if import_type is ScenarioType.BUDGET else None,
            status=ImportJobStatus.CREATED,
            original_filename=filename[:255],
            object_key=None,
            sha256=sha256.lower(),
            size_bytes=size_bytes,
            media_type="application/octet-stream",
            template_version=template_version or "1.0",
            mapping_json={},
            row_count=0,
            valid_count=0,
            error_count=0,
            warning_count=0,
            period_min=None,
            period_max=None,
            valid_amount_total="0.0000",
            idempotency_fingerprint=None,
            started_at=None,
            completed_at=None,
            created_at=self._clock.now(),
            failure_code=None,
            create_missing_dimensions=False,
            sheet_name=None,
            trace_id=context.trace_id,
        )
        self._jobs(context.organization_id).add(job)
        record_audit(
            self._audits,
            clock=self._clock,
            ids=self._ids,
            organization_id=context.organization_id,
            actor_id=context.user.id,
            action=IMPORT_CREATED,
            resource_type="import_job",
            resource_id=job.id,
            trace_id=context.trace_id,
            metadata={"import_type": import_type.value, "size_bytes": size_bytes},
        )
        metrics_registry().record_job_status(
            job.status.value,
            job_type=import_type.value,
            bytes_processed=size_bytes,
        )
        return job

    def upload_descriptor(self, context: TenantContext, job: ImportJob) -> UploadTarget:
        key = job.object_key or self._storage.generate_key(
            organization_id=context.organization_id,
            namespace=f"imports/{job.id}",
            name=job.original_filename,
        )
        self._storage.assert_tenant_key(key, organization_id=context.organization_id)
        signed = self._storage.presign_put(
            key,
            organization_id=context.organization_id,
            content_type="application/octet-stream",
            expires_in=900,
        )
        if signed is None:
            return UploadTarget(
                mode="proxy",
                method="PUT",
                url=f"/api/v1/imports/{job.id}/content",
            )
        if job.object_key is None:
            self._jobs(context.organization_id).save(replace(job, object_key=key))
        return UploadTarget(mode="presigned", method=signed.method, url=signed.url)

    def upload_content(
        self,
        context: TenantContext,
        *,
        job_id: UUID,
        content: bytes,
        media_type: str | None,
    ) -> ImportJob:
        require_permission(context.role, Permission.IMPORT)
        enforce_limit(
            "upload",
            context.user.id,
            organization_id=context.organization_id,
            limit=self._settings.rate_limit_upload_per_minute,
        )
        job = self.get(context, job_id)
        if job.status not in {ImportJobStatus.CREATED, ImportJobStatus.UPLOADED}:
            raise ConflictError("IMPORT_STATE", "Este trabajo ya no admite un archivo nuevo.")
        if len(content) > self._settings.max_upload_bytes:
            raise PayloadTooLargeError()
        if len(content) != job.size_bytes:
            raise ValidationError(
                "UNSUPPORTED_FILE", "El tamaño del archivo no coincide con el declarado."
            )
        digest = sha256_hex(content)
        if digest != job.sha256:
            raise ValidationError(
                "UNSUPPORTED_FILE", "La huella del archivo no coincide con la declarada."
            )
        self._parser.parse(job.original_filename, content, media_type=media_type)
        key = job.object_key or self._storage.generate_key(
            organization_id=context.organization_id,
            namespace=f"imports/{job.id}",
            name=job.original_filename,
        )
        self._storage.assert_tenant_key(key, organization_id=context.organization_id)
        self._storage.put(key, content, content_type=media_type or "application/octet-stream")
        updated = job.mark_uploaded(
            object_key=key,
            media_type=media_type or "application/octet-stream",
            now=self._clock.now(),
        )
        self._jobs(context.organization_id).save(updated)
        return updated

    def _persist_processing(self, job: ImportJob, *, trace_id: str) -> ImportJob:
        updated = job.mark_processing(now=self._clock.now(), trace_id=trace_id)
        self._jobs(job.organization_id).save(updated)
        self._session.flush()
        return updated

    def validate(
        self,
        context: TenantContext,
        *,
        job_id: UUID,
        mapping: dict[str, str],
        create_missing_dimensions: bool,
        amount_locale: str = "en",
        sheet_name: str | None = None,
        delimiter: str | None = None,
    ) -> ImportJob:
        require_permission(context.role, Permission.IMPORT)
        job = self.get(context, job_id)
        previous = job
        job = self._persist_processing(job, trace_id=context.trace_id)
        organization = self._require_org(context.organization_id)

        def work() -> ImportJob:
            return self._validate_body(
                context,
                job=job,
                previous=previous,
                organization=organization,
                mapping=mapping,
                create_missing_dimensions=create_missing_dimensions,
                amount_locale=amount_locale,
                sheet_name=sheet_name,
                delimiter=delimiter,
            )

        return self._executor.run("validate", work)

    def _validate_body(
        self,
        context: TenantContext,
        *,
        job: ImportJob,
        previous: ImportJob,
        organization: Organization,
        mapping: dict[str, str],
        create_missing_dimensions: bool,
        amount_locale: str,
        sheet_name: str | None,
        delimiter: str | None,
    ) -> ImportJob:
        started = perf_counter()
        try:
            columns = validate_mapping(mapping)
            table = self._load_table(job, sheet_name=sheet_name, delimiter=delimiter)
            if table.delimiter_ambiguous and delimiter is None:
                raise ValidationError(
                    "UNSUPPORTED_FILE",
                    "El delimitador del CSV es ambiguo y debe confirmarse.",
                    field_errors=[
                        field_issue(
                            "delimiter",
                            "UNSUPPORTED_FILE",
                            "Confirma si el archivo usa coma, punto y coma o tabulador.",
                        )
                    ],
                )
            payload = {
                "columns": columns,
                "amount_locale": amount_locale,
                "delimiter": delimiter or table.delimiter,
            }
            fingerprint = job.fingerprint_for(payload)
            existing = self._jobs(context.organization_id).get_by_fingerprint(fingerprint)
            if existing is not None and existing.id != job.id:
                self._jobs(context.organization_id).save(previous)
                if existing.status is ImportJobStatus.PROCESSING:
                    raise ConflictError(
                        "IMPORT_ALREADY_IN_PROGRESS",
                        "Ya hay un trabajo en curso con la misma huella.",
                    )
                return existing
            create_missing = can_create_missing_dimensions(
                flag=create_missing_dimensions, role=context.role
            )
            if create_missing_dimensions and not create_missing and context.role is not Role.ADMIN:
                create_missing = False
            version_fy = self._fiscal_year_for_job(context, job)
            normalized, issues = self._collect_rows(
                table.rows,
                mapping=columns,
                amount_locale=amount_locale,
                organization=organization,
                fiscal_year=version_fy,
                create_missing=create_missing,
                context=context,
            )
            periods = [item.period_start for item in normalized]
            total = sum((item.amount.value for item in normalized), Decimal("0.0000"))
            updated = job.mark_validated(
                mapping=payload,
                fingerprint=fingerprint,
                row_count=len(table.rows),
                valid_count=len(normalized),
                error_count=sum(1 for item in issues if item.severity is ImportErrorSeverity.ERROR),
                warning_count=sum(
                    1 for item in issues if item.severity is ImportErrorSeverity.WARNING
                ),
                period_min=min(periods) if periods else None,
                period_max=max(periods) if periods else None,
                valid_amount_total=f"{total:.4f}",
                create_missing_dimensions=create_missing,
                sheet_name=table.sheet_name,
                now=self._clock.now(),
            )
            try:
                self._jobs(context.organization_id).save(updated)
                self._errors(context.organization_id).replace_for_job(job.id, issues, ids=self._ids)
                self._session.flush()
            except IntegrityError as exc:
                raise ConflictError(
                    "IMPORT_ALREADY_IN_PROGRESS",
                    "Ya hay un trabajo en curso con la misma huella.",
                ) from exc
            record_audit(
                self._audits,
                clock=self._clock,
                ids=self._ids,
                organization_id=context.organization_id,
                actor_id=context.user.id,
                action=IMPORT_VALIDATED,
                resource_type="import_job",
                resource_id=updated.id,
                trace_id=context.trace_id,
                metadata={
                    "status": updated.status.value,
                    "valid_count": updated.valid_count,
                    "error_count": updated.error_count,
                    "warning_count": updated.warning_count,
                },
            )
            metrics_registry().record_job_status(
                updated.status.value,
                job_type=updated.import_type.value,
                phase="validation",
                duration_ms=(perf_counter() - started) * 1000,
                rows_processed=updated.row_count,
                rows_error=updated.error_count,
                bytes_processed=updated.size_bytes,
            )
            return updated
        except DomainError:
            self._jobs(context.organization_id).save(previous)
            raise
        except Exception:
            failed = job.mark_failed(code="JOB_INTERRUPTED", now=self._clock.now())
            self._jobs(context.organization_id).save(failed)
            record_audit(
                self._audits,
                clock=self._clock,
                ids=self._ids,
                organization_id=context.organization_id,
                actor_id=context.user.id,
                action=IMPORT_FAILED,
                resource_type="import_job",
                resource_id=failed.id,
                trace_id=context.trace_id,
                metadata={"failure_code": "JOB_INTERRUPTED"},
                outcome="failed",
            )
            metrics_registry().record_job_status("failed")
            raise

    def preview(
        self, context: TenantContext, *, job_id: UUID, cursor: str | None, limit: int | None
    ) -> ImportPreview:
        job = self.get(context, job_id)
        if job.status in {ImportJobStatus.CREATED}:
            raise ConflictError("IMPORT_STATE", "Valida el archivo para ver la vista previa.")
        stored_delimiter = (
            str(job.mapping_json["delimiter"])
            if job.mapping_json and job.mapping_json.get("delimiter")
            else None
        )
        table = self._load_table(job, sheet_name=job.sheet_name, delimiter=stored_delimiter)
        columns = dict(job.mapping_json.get("columns", {})) if job.mapping_json else {}
        amount_locale = (
            str(job.mapping_json.get("amount_locale", "en")) if job.mapping_json else "en"
        )
        organization = self._require_org(context.organization_id)
        page_limit = clamp_preview_limit(limit)
        offset = 0
        parsed = decode_cursor(cursor)
        if parsed is not None:
            try:
                offset = max(0, int(parsed.get("offset", "0")))
            except ValueError as exc:
                raise ValidationError(
                    "INVALID_CURSOR",
                    "El cursor de paginación no es válido.",
                    field_errors=[
                        field_issue(
                            "cursor", "INVALID_CURSOR", "El cursor de paginación no es válido."
                        )
                    ],
                ) from exc
        sanitized: list[dict[str, str]] = []
        new_accounts = 0
        new_departments = 0
        new_cost_centers = 0
        replaced_records = 0
        if not columns:
            sanitized = _source_preview_rows(table, offset=offset, page_limit=page_limit)
        if columns:
            version_fy = self._fiscal_year_for_job(context, job)
            normalized, _issues = self._collect_rows(
                table.rows,
                mapping=columns,
                amount_locale=amount_locale,
                organization=organization,
                fiscal_year=version_fy,
                create_missing=job.create_missing_dimensions,
                context=context,
            )
            accounts = SqlAccountRepository(self._session, context.organization_id)
            departments = SqlDepartmentRepository(self._session, context.organization_id)
            cost_centers = SqlCostCenterRepository(self._session, context.organization_id)
            seen_accounts: set[str] = set()
            seen_departments: set[str] = set()
            seen_cost_centers: set[str] = set()
            overlap_keys: list[tuple[object, object, object, object]] = []
            index = 0
            for item in normalized:
                if (
                    accounts.get_by_code(item.account_code) is None
                    and item.account_code not in seen_accounts
                ):
                    new_accounts += 1
                    seen_accounts.add(item.account_code)
                if (
                    departments.get_by_code(item.department_code) is None
                    and item.department_code not in seen_departments
                ):
                    new_departments += 1
                    seen_departments.add(item.department_code)
                if (
                    cost_centers.get_by_code(item.cost_center_code) is None
                    and item.cost_center_code not in seen_cost_centers
                ):
                    new_cost_centers += 1
                    seen_cost_centers.add(item.cost_center_code)
                account = accounts.get_by_code(item.account_code)
                department = departments.get_by_code(item.department_code)
                cost_center = cost_centers.get_by_code(item.cost_center_code)
                if account and department and cost_center:
                    overlap_keys.append(
                        (item.period_start, account.id, department.id, cost_center.id)
                    )
                if index < offset:
                    index += 1
                    continue
                sanitized.append(_preview_row(item))
                index += 1
                if len(sanitized) > page_limit:
                    break
            replaced_records = SqlFinancialEntryRepository(
                self._session, context.organization_id
            ).count_matching(
                scenario_type=job.import_type.value,
                budget_version_id=job.budget_version_id,
                keys=overlap_keys,
            )
        has_more = len(sanitized) > page_limit
        rows = sanitized[:page_limit]
        next_cursor = encode_cursor({"offset": str(offset + page_limit)}) if has_more else None
        stored_issues = (
            self._errors(context.organization_id).list_all(job.id)
            if job.status not in {ImportJobStatus.CREATED, ImportJobStatus.UPLOADED}
            else []
        )
        return ImportPreview(
            job=job,
            headers=table.headers,
            proposed_mapping=propose_mapping(table.headers),
            rows=rows,
            new_accounts=new_accounts,
            new_departments=new_departments,
            new_cost_centers=new_cost_centers,
            replaced_records=replaced_records,
            sha256_short=abbreviated_sha256(job.sha256),
            delimiter=table.delimiter,
            delimiter_ambiguous=table.delimiter_ambiguous,
            available_sheets=list(table.available_sheets),
            error_groups=group_import_issues(stored_issues),
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def list_errors(
        self, context: TenantContext, *, job_id: UUID, cursor: str | None, limit: int | None
    ) -> Page[ImportIssue]:
        self.get(context, job_id)
        return self._errors(context.organization_id).list_page(
            job_id, cursor=cursor, limit=clamp_limit(limit)
        )

    def error_report(self, context: TenantContext, *, job_id: UUID) -> bytes:
        job = self.get(context, job_id)
        issues = self._errors(context.organization_id).list_all(job.id)
        rows = [
            [
                str(item.row_number),
                item.field,
                item.code,
                item.message,
                item.severity.value,
                item.raw_value_redacted,
            ]
            for item in issues
        ]
        return render_csv(
            ("row_number", "field", "code", "message", "severity", "raw_value_redacted"),
            rows,
        )

    def commit(self, context: TenantContext, *, job_id: UUID, idempotency_key: str) -> ImportJob:
        require_permission(context.role, Permission.IMPORT)
        require_idempotency_key(idempotency_key)
        job = self.get(context, job_id)
        replay = replay_or_reserve(
            self._session,
            organization_id=context.organization_id,
            user_id=context.user.id,
            operation="import.commit",
            idempotency_key=idempotency_key,
            resource_id=job.id,
            request_hash=hash_payload("import.commit", str(job.id), job.sha256),
            clock=self._clock,
            ids=self._ids,
        )
        if replay is not None:
            existing = self.get(context, replay)
            return existing
        job.assert_committable()
        job = self._persist_processing(job, trace_id=context.trace_id)
        return self._executor.run("apply", lambda: self._commit_body(context, job=job))

    def _commit_body(self, context: TenantContext, *, job: ImportJob) -> ImportJob:
        if job.idempotency_fingerprint:
            other = self._jobs(context.organization_id).get_by_fingerprint(
                job.idempotency_fingerprint
            )
            if other is not None and other.id != job.id:
                if other.status is ImportJobStatus.APPLIED:
                    return other
                raise ConflictError(
                    "IMPORT_ALREADY_IN_PROGRESS",
                    "Ya hay un trabajo en curso con la misma huella.",
                )
        content = self._storage.get(job.object_key or "")
        job.assert_same_hash(sha256_hex(content))
        organization = self._require_org(context.organization_id)
        columns = dict(job.mapping_json["columns"])
        amount_locale = str(job.mapping_json.get("amount_locale", "en"))
        stored_delimiter = (
            str(job.mapping_json["delimiter"])
            if job.mapping_json and job.mapping_json.get("delimiter")
            else None
        )
        table = self._parser.parse(
            job.original_filename,
            content,
            media_type=job.media_type,
            sheet_name=job.sheet_name,
            delimiter=stored_delimiter,
        )
        version_fy = self._fiscal_year_for_job(context, job)
        normalized, issues = self._collect_rows(
            table.rows,
            mapping=columns,
            amount_locale=amount_locale,
            organization=organization,
            fiscal_year=version_fy,
            create_missing=job.create_missing_dimensions,
            context=context,
        )
        error_count = sum(1 for item in issues if item.severity is ImportErrorSeverity.ERROR)
        total = sum((item.amount.value for item in normalized), Decimal("0.0000"))
        if error_count > 0 or f"{total:.4f}" != job.valid_amount_total:
            raise ConflictError(
                "IMPORT_VALIDATION_FAILED",
                "El archivo contiene errores que deben corregirse.",
            )
        if job.import_type is ScenarioType.BUDGET:
            self._require_version_for_create(
                context, import_type=job.import_type, budget_version_id=job.budget_version_id
            )
        started = perf_counter()
        entries = [self._to_entry(context, job, item, organization) for item in normalized]
        SqlFinancialEntryRepository(self._session, context.organization_id).add_many(entries)
        updated = job.mark_applied(now=self._clock.now())
        self._jobs(context.organization_id).save(updated)
        record_audit(
            self._audits,
            clock=self._clock,
            ids=self._ids,
            organization_id=context.organization_id,
            actor_id=context.user.id,
            action=IMPORT_COMMITTED,
            resource_type="import_job",
            resource_id=updated.id,
            trace_id=context.trace_id,
            metadata={"valid_count": updated.valid_count, "error_count": updated.error_count},
        )
        metrics_registry().record_job_status(
            updated.status.value,
            job_type=updated.import_type.value,
            phase="apply",
            duration_ms=(perf_counter() - started) * 1000,
            rows_processed=updated.valid_count,
            rows_error=updated.error_count,
            bytes_processed=updated.size_bytes,
        )
        return updated

    def cancel(self, context: TenantContext, *, job_id: UUID) -> ImportJob:
        require_permission(context.role, Permission.IMPORT)
        job = self.get(context, job_id)
        updated = job.cancel(now=self._clock.now())
        self._jobs(context.organization_id).save(updated)
        record_audit(
            self._audits,
            clock=self._clock,
            ids=self._ids,
            organization_id=context.organization_id,
            actor_id=context.user.id,
            action=IMPORT_CANCELLED,
            resource_type="import_job",
            resource_id=updated.id,
            trace_id=context.trace_id,
        )
        return updated

    def _load_table(
        self,
        job: ImportJob,
        *,
        sheet_name: str | None = None,
        delimiter: str | None = None,
    ) -> WorkbookTable:
        if not job.object_key:
            raise ConflictError("IMPORT_STATE", "Primero debes cargar el archivo.")
        content = self._storage.get(job.object_key)
        return self._parser.parse(
            job.original_filename,
            content,
            media_type=job.media_type,
            sheet_name=sheet_name,
            delimiter=delimiter,
        )

    def _collect_rows(
        self,
        rows: list[ParsedCellRow],
        *,
        mapping: dict[str, str],
        amount_locale: str,
        organization: Organization,
        fiscal_year: int | None,
        create_missing: bool,
        context: TenantContext,
    ) -> tuple[list[NormalizedImportRow], list[ImportIssue]]:
        normalized: list[NormalizedImportRow] = []
        issues: list[ImportIssue] = []
        seen: dict[tuple[object, ...], int] = {}
        last_data_index = -1
        inspected: list[tuple[object, NormalizedImportRow | None, list[ImportIssue]]] = []
        for row in rows:
            item, row_issues = normalize_row(
                row,
                mapping=mapping,
                amount_locale=amount_locale,
                functional=organization.functional_currency,
                fiscal_year=fiscal_year,
                fiscal_year_start_month=organization.fiscal_year_start_month,
            )
            inspected.append((row, item, row_issues))
            empty_warning = any(
                issue.code == "EMPTY_OPTIONAL_VALUE" and issue.field == "row"
                for issue in row_issues
            )
            if not empty_warning:
                last_data_index = len(inspected) - 1
        for index, (_row, item, row_issues) in enumerate(inspected):
            empty_warning = any(
                issue.code == "EMPTY_OPTIONAL_VALUE" and issue.field == "row"
                for issue in row_issues
            )
            if empty_warning and index > last_data_index:
                continue
            issues.extend(row_issues)
            if item is None:
                continue
            key = item.duplicate_key()
            if key in seen:
                issues.append(
                    ImportIssue(
                        row_number=item.row_number,
                        field="row",
                        code="DUPLICATE_ROW",
                        message="La fila está duplicada dentro del archivo.",
                        raw_value_redacted=redact_cell(item.account_code),
                        severity=ImportErrorSeverity.ERROR,
                    )
                )
                continue
            seen[key] = item.row_number
            issues.extend(
                self._dimension_issues(
                    item, create_missing=create_missing, organization_id=context.organization_id
                )
            )
            if any(
                issue.row_number == item.row_number and issue.severity is ImportErrorSeverity.ERROR
                for issue in issues
            ):
                continue
            normalized.append(item)
        return normalized, issues

    def _dimension_issues(
        self, item: NormalizedImportRow, *, create_missing: bool, organization_id: UUID
    ) -> list[ImportIssue]:
        issues: list[ImportIssue] = []
        accounts = SqlAccountRepository(self._session, organization_id)
        departments = SqlDepartmentRepository(self._session, organization_id)
        cost_centers = SqlCostCenterRepository(self._session, organization_id)
        if accounts.get_by_code(item.account_code) is None:
            if create_missing and not item.account_name:
                issues.append(
                    ImportIssue(
                        row_number=item.row_number,
                        field="account_name",
                        code="MISSING_COLUMN",
                        message="El nombre de la cuenta es obligatorio al crear dimensiones.",
                        raw_value_redacted=item.account_code,
                        severity=ImportErrorSeverity.ERROR,
                    )
                )
            else:
                issues.append(
                    ImportIssue(
                        row_number=item.row_number,
                        field="account_code",
                        code="UNKNOWN_ACCOUNT",
                        message="La cuenta no existe."
                        if not create_missing
                        else "La cuenta se creará al confirmar.",
                        raw_value_redacted=item.account_code,
                        severity=ImportErrorSeverity.WARNING
                        if create_missing
                        else ImportErrorSeverity.ERROR,
                    )
                )
        if departments.get_by_code(item.department_code) is None:
            if create_missing and not item.department_name:
                issues.append(
                    ImportIssue(
                        row_number=item.row_number,
                        field="department_name",
                        code="MISSING_COLUMN",
                        message="El nombre del departamento es obligatorio al crear dimensiones.",
                        raw_value_redacted=item.department_code,
                        severity=ImportErrorSeverity.ERROR,
                    )
                )
            else:
                issues.append(
                    ImportIssue(
                        row_number=item.row_number,
                        field="department_code",
                        code="UNKNOWN_DEPARTMENT",
                        message="El departamento no existe."
                        if not create_missing
                        else "El departamento se creará al confirmar.",
                        raw_value_redacted=item.department_code,
                        severity=ImportErrorSeverity.WARNING
                        if create_missing
                        else ImportErrorSeverity.ERROR,
                    )
                )
        if cost_centers.get_by_code(item.cost_center_code) is None:
            issues.append(
                ImportIssue(
                    row_number=item.row_number,
                    field="cost_center_code",
                    code="UNKNOWN_COST_CENTER",
                    message="El centro de costo no existe."
                    if not create_missing
                    else "El centro de costo se creará al confirmar.",
                    raw_value_redacted=item.cost_center_code,
                    severity=ImportErrorSeverity.WARNING
                    if create_missing
                    else ImportErrorSeverity.ERROR,
                )
            )
        return issues

    def _to_entry(
        self,
        context: TenantContext,
        job: ImportJob,
        item: NormalizedImportRow,
        organization: Organization,
    ) -> FinancialEntry:
        now = self._clock.now()
        account = self._resolve_account(context, item, now)
        department = self._resolve_department(context, item, now)
        cost_center = self._resolve_cost_center(context, item, now)
        entry = FinancialEntry(
            id=self._ids.new_id(),
            organization_id=context.organization_id,
            import_job_id=job.id,
            scenario_type=job.import_type,
            budget_version_id=job.budget_version_id,
            period_start=item.period_start,
            fiscal_year=item.fiscal_year,
            account_id=account.id,
            department_id=department.id,
            cost_center_id=cost_center.id,
            amount=item.amount,
            currency=organization.functional_currency,
            source_row_number=item.row_number,
            source_reference=item.source_reference,
            created_at=now,
        )
        entry.assert_consistent_with(organization)
        return entry

    def _resolve_account(
        self, context: TenantContext, item: NormalizedImportRow, now: datetime
    ) -> Account:
        repo = SqlAccountRepository(self._session, context.organization_id)
        current = repo.get_by_code(item.account_code)
        if current is not None:
            return current
        if not context or not item.account_name:
            raise ValidationError("UNKNOWN_ACCOUNT", "La cuenta no existe.")
        account_type = AccountType(item.account_type) if item.account_type else AccountType.OTHER
        created = Account(
            id=self._ids.new_id(),
            organization_id=context.organization_id,
            code=normalize_code(item.account_code),
            name=normalize_name(item.account_name, field="account_name", max_length=160),
            account_type=account_type,
            parent_id=None,
            status=DimensionStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        repo.add(created)
        self._session.flush()
        return created

    def _resolve_department(
        self, context: TenantContext, item: NormalizedImportRow, now: datetime
    ) -> Department:
        repo = SqlDepartmentRepository(self._session, context.organization_id)
        current = repo.get_by_code(item.department_code)
        if current is not None:
            return current
        created = Department(
            id=self._ids.new_id(),
            organization_id=context.organization_id,
            code=normalize_code(item.department_code),
            name=normalize_name(
                item.department_name or item.department_code,
                field="department_name",
                max_length=160,
            ),
            status=DimensionStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        repo.add(created)
        self._session.flush()
        return created

    def _resolve_cost_center(
        self, context: TenantContext, item: NormalizedImportRow, now: datetime
    ) -> CostCenter:
        repo = SqlCostCenterRepository(self._session, context.organization_id)
        current = repo.get_by_code(item.cost_center_code or UNASSIGNED_CODE)
        if current is not None:
            return current
        created = CostCenter(
            id=self._ids.new_id(),
            organization_id=context.organization_id,
            code=normalize_code(item.cost_center_code),
            name=normalize_name(
                item.cost_center_name or item.cost_center_code,
                field="cost_center_name",
                max_length=160,
            ),
            status=DimensionStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        repo.add(created)
        self._session.flush()
        return created

    def _require_org(self, organization_id: UUID) -> Organization:
        organization = self._orgs.get(organization_id)
        if organization is None:
            raise NotFoundError()
        return organization

    def _require_version_for_create(
        self,
        context: TenantContext,
        *,
        import_type: ScenarioType,
        budget_version_id: UUID | None,
    ) -> BudgetVersion | None:
        if import_type is ScenarioType.ACTUAL:
            if budget_version_id is not None:
                raise ValidationError(
                    "BUDGET_VERSION_FORBIDDEN",
                    "Las filas reales no aceptan versión de presupuesto.",
                )
            return None
        if budget_version_id is None:
            raise ValidationError(
                "BUDGET_VERSION_REQUIRED",
                "Las filas de presupuesto requieren una versión.",
            )
        version = SqlBudgetVersionRepository(self._session, context.organization_id).get(
            budget_version_id
        )
        if version is None:
            raise NotFoundError()
        version.assert_accepts_entries()
        return version

    def _fiscal_year_for_job(self, context: TenantContext, job: ImportJob) -> int | None:
        if job.import_type is not ScenarioType.BUDGET or job.budget_version_id is None:
            return None
        version = SqlBudgetVersionRepository(self._session, context.organization_id).get(
            job.budget_version_id
        )
        return version.fiscal_year if version else None


def _preview_row(item: NormalizedImportRow) -> dict[str, str]:
    return {
        "row_number": str(item.row_number),
        "period": item.period_start.isoformat(),
        "account_code": item.account_code,
        "department_code": item.department_code,
        "cost_center_code": item.cost_center_code,
        "amount": item.amount.as_text(),
        "currency": item.currency,
    }


def _source_preview_rows(
    table: WorkbookTable, *, offset: int, page_limit: int
) -> list[dict[str, str]]:
    sanitized: list[dict[str, str]] = []
    for index, row in enumerate(table.rows):
        if index < offset:
            continue
        sanitized.append(
            {"row_number": str(row.row_number)}
            | {
                header: redact_cell(row.values.get(header, ""))
                for header in table.headers
                if header
            }
        )
        if len(sanitized) > page_limit:
            break
    return sanitized
