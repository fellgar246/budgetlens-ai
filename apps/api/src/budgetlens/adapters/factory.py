from __future__ import annotations

from sqlalchemy.orm import Session

from budgetlens.adapters.ai import build_ai_provider_from_settings
from budgetlens.adapters.exports import build_export_executor
from budgetlens.adapters.identity import build_identity_provider
from budgetlens.adapters.imports import build_import_executor
from budgetlens.adapters.parsing import OpenpyxlWorkbookParser, ParseLimits
from budgetlens.adapters.persistence.repositories import SqlUserRepository
from budgetlens.adapters.storage import LocalObjectStorage, S3ObjectStorage
from budgetlens.config import Settings
from budgetlens.ports.ai import AIProvider
from budgetlens.ports.exports import ExportExecutor
from budgetlens.ports.identity import IdentityProvider
from budgetlens.ports.imports import ImportExecutor
from budgetlens.ports.parsing import WorkbookParser
from budgetlens.ports.storage import ObjectStorage


def build_object_storage(settings: Settings) -> ObjectStorage:
    if settings.object_storage_backend == "s3":
        return S3ObjectStorage(
            bucket=settings.s3_bucket,
            region=settings.s3_region,
            prefix=settings.s3_prefix,
            endpoint_url=settings.s3_endpoint_url,
            key_pepper=settings.storage_key_pepper,
        )
    return LocalObjectStorage(settings.local_storage_path, key_pepper=settings.storage_key_pepper)


def build_ai_provider(settings: Settings) -> AIProvider:
    return build_ai_provider_from_settings(settings)


def build_identity_adapter(settings: Settings, session: Session) -> IdentityProvider:
    return build_identity_provider(
        auth_mode=settings.auth_mode,
        app_env=settings.app_env,
        users=SqlUserRepository(session),
        settings=settings,
    )


def build_import_runner(settings: Settings) -> ImportExecutor:
    return build_import_executor(settings.import_executor)


def build_export_runner(settings: Settings) -> ExportExecutor:
    return build_export_executor(settings.export_executor)


def build_workbook_parser(settings: Settings | None = None) -> WorkbookParser:
    if settings is None:
        return OpenpyxlWorkbookParser()
    return OpenpyxlWorkbookParser(
        ParseLimits(
            max_sheets=settings.import_max_sheets,
            max_rows=settings.import_max_rows,
            max_columns=settings.import_max_columns,
            max_cells=settings.import_max_cells,
        )
    )
