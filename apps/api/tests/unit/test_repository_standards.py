from __future__ import annotations

import ast
import re
from pathlib import Path

from budgetlens.presentation import schemas, schemas_ops

REPO_ROOT = Path(__file__).resolve().parents[4]
SOURCE_ROOTS = (
    REPO_ROOT / "apps",
    REPO_ROOT / "packages",
    REPO_ROOT / "docs",
    REPO_ROOT / "scripts",
    REPO_ROOT / "infrastructure",
)
ROOT_FILES = (
    REPO_ROOT / "README.md",
    REPO_ROOT / "Makefile",
    REPO_ROOT / "compose.yaml",
    REPO_ROOT / ".env.example",
)
SKIP_PARTS = {
    ".venv",
    "node_modules",
    ".next",
    "out",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
}
SKIP_NAMES = {
    "openapi.json",
    "pnpm-lock.yaml",
    "uv.lock",
    "package-lock.json",
}
SPEC_MARKERS = re.compile(
    "|".join(
        (
            "spec" + "-docs",
            "specs/" + "0[0-5]",
            "PLAN_" + "0[0-9]",
            "PLAN_" + "1[01]",
            "AGENT_" + "EXECUTION",
            "BUDGETLENS_" + "UI_GUIDELINES",
        )
    )
)
GUARD_FILES = {"test_traceability.py"}
REQUIRED_LAYOUT = (
    "apps/api/src/budgetlens/domain",
    "apps/api/src/budgetlens/application",
    "apps/api/src/budgetlens/ports",
    "apps/api/src/budgetlens/adapters",
    "apps/api/src/budgetlens/presentation",
    "apps/api/migrations",
    "apps/api/tests",
    "apps/web/src/app",
    "apps/web/src/components",
    "apps/web/src/features",
    "apps/web/src/lib",
    "apps/web/tests",
    "packages/api-client",
    "infrastructure/terraform/bootstrap",
    "infrastructure/terraform/modules",
    "infrastructure/terraform/environments",
    "sample-data",
    "scripts",
    "docs",
)


def test_repository_layout_matches_the_pinned_tree() -> None:
    missing = [item for item in REQUIRED_LAYOUT if not (REPO_ROOT / item).exists()]
    assert missing == []
    assert (REPO_ROOT / "compose.yaml").is_file()
    assert (REPO_ROOT / ".python-version").is_file()
    assert (REPO_ROOT / ".node-version").is_file()


def test_product_artifacts_do_not_cite_specification_paths() -> None:
    offenders: list[str] = []
    paths = [path for root in SOURCE_ROOTS for path in root.rglob("*") if path.is_file()]
    paths.extend(ROOT_FILES)
    for path in paths:
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.name in SKIP_NAMES or path.name in GUARD_FILES:
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".ico", ".woff", ".woff2"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if SPEC_MARKERS.search(text):
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == []


def test_request_schemas_are_separate_from_domain_entities() -> None:
    request_models = [
        getattr(module, name)
        for module in (schemas, schemas_ops)
        for name in dir(module)
        if name.endswith("Request")
    ]
    assert request_models
    for model in request_models:
        assert model.__module__.startswith("budgetlens.presentation")
        assert "domain" not in model.__module__


def test_money_response_fields_are_decimal_strings() -> None:
    offenders: list[str] = []
    for module in (schemas, schemas_ops):
        for name in dir(module):
            model = getattr(module, name)
            fields = getattr(model, "model_fields", None)
            if not fields:
                continue
            for field_name, field in fields.items():
                if field_name not in {"amount", "valid_amount_total"} and not field_name.endswith(
                    "_amount"
                ):
                    continue
                annotation = str(field.annotation)
                if "str" not in annotation:
                    offenders.append(f"{module.__name__}.{name}.{field_name}: {annotation}")
    assert offenders == []


def test_presentation_does_not_redefine_domain_error_handlers() -> None:
    tree = ast.parse(
        (REPO_ROOT / "apps/api/src/budgetlens/presentation/errors.py").read_text(encoding="utf-8")
    )
    names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and node.name.endswith("_handler")
    }
    assert {"domain_handler", "validation_handler", "unhandled_handler"} <= names
