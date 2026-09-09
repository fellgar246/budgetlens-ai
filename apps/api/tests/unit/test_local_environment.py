from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
COMPOSE = (REPO_ROOT / "compose.yaml").read_text(encoding="utf-8")
MAKEFILE = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
ENV_EXAMPLE = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
GITIGNORE = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
DOCTOR = (REPO_ROOT / "scripts" / "doctor.sh").read_text(encoding="utf-8")
BOOTSTRAP = (REPO_ROOT / "scripts" / "bootstrap.sh").read_text(encoding="utf-8")
RESET = (REPO_ROOT / "scripts" / "reset-local-data.sh").read_text(encoding="utf-8")
ENTRYPOINT = (REPO_ROOT / "apps" / "api" / "docker-entrypoint.sh").read_text(encoding="utf-8")
WEB_DOCKERFILE = (REPO_ROOT / "apps" / "web" / "Dockerfile").read_text(encoding="utf-8")
README = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

CANONICAL_TARGETS = (
    "doctor",
    "bootstrap",
    "dev",
    "stop",
    "logs",
    "migrate",
    "seed",
    "test",
    "test-integration",
    "test-e2e",
    "lint",
    "format",
    "openapi",
    "clean-generated",
    "reset-local-data",
)

INSTALL_COMMANDS = (
    "brew install",
    "apt-get install",
    "pip install",
    "pip3 install",
    "npm install -g",
)


def test_compose_defines_local_services_ports_and_storage() -> None:
    for service in ("postgres:", "api:", "web:", "worker:"):
        assert service in COMPOSE
    assert "${WEB_PORT:-3000}:3000" in COMPOSE
    assert "${API_PORT:-8000}:8000" in COMPOSE
    assert "${POSTGRES_PORT:-5433}:5432" in COMPOSE
    assert "postgres_data:" in COMPOSE
    assert COMPOSE.count("healthcheck:") >= 3
    assert "OBJECT_STORAGE_BACKEND: local" in COMPOSE
    assert "./var/storage:/var/lib/budgetlens/storage" in COMPOSE
    assert "localstack" not in COMPOSE.lower()
    assert "minio" not in COMPOSE.lower()


def test_compose_uses_development_web_and_optional_api_reload() -> None:
    assert "target: development" in COMPOSE
    assert "API_RELOAD: ${API_RELOAD:-1}" in COMPOSE
    assert "FROM deps AS development" in WEB_DOCKERFILE
    assert 'CMD ["pnpm", "--filter", "web", "dev"]' in WEB_DOCKERFILE


def test_worker_is_an_optional_compose_profile() -> None:
    worker_block = COMPOSE[COMPOSE.index("worker:") :]
    assert 'profiles: ["worker"]' in worker_block or "profiles:\n      - worker" in worker_block
    assert 'command: ["worker"]' in worker_block
    assert "  worker)" in ENTRYPOINT
    assert "python -m budgetlens worker" in ENTRYPOINT


def test_api_entrypoint_reloads_only_when_requested_and_does_not_auto_seed() -> None:
    api_case = ENTRYPOINT.split("api)", 1)[1].split("worker)", 1)[0]
    assert "alembic upgrade head" in api_case
    assert "RUN_MIGRATIONS_ON_START" in api_case
    assert "API_RELOAD" in api_case
    assert "--reload" in api_case
    assert "seed" not in api_case


def test_makefile_exposes_the_canonical_local_commands() -> None:
    missing = [name for name in CANONICAL_TARGETS if not re.search(rf"^{name}:", MAKEFILE, re.M)]
    assert missing == []
    stop_block = MAKEFILE.split("stop:", 1)[1].split("\n\n", 1)[0]
    assert "docker compose stop" in stop_block
    assert "down --volumes" not in stop_block
    clean_block = MAKEFILE.split("clean-generated:", 1)[1].split("\n\n", 1)[0]
    assert "var/storage" not in clean_block
    assert "postgres_data" not in clean_block


def test_env_example_documents_local_defaults() -> None:
    for token in (
        "APP_ENV=local",
        "AUTH_MODE=dev",
        "AI_PROVIDER=stub",
        "OBJECT_STORAGE_BACKEND=local",
        "MAX_UPLOAD_BYTES=26214400",
        "API_RELOAD=1",
        "WEB_PORT=3000",
        "API_PORT=8000",
        "POSTGRES_PORT=5433",
        "budgetlens_local_only",
        "NEXT_PUBLIC_AUTH_MODE=dev",
        "NEXT_PUBLIC_OIDC_ISSUER=",
    ):
        assert token in ENV_EXAMPLE
    assert "development-only" in ENV_EXAMPLE
    assert "must not be reused in AWS" in ENV_EXAMPLE


def test_ignored_paths_cover_env_and_local_uploads() -> None:
    for token in (".env\n", "var/", "uploads/", "local-storage/"):
        assert token in GITIGNORE


def test_doctor_checks_tools_without_installing() -> None:
    for command in INSTALL_COMMANDS:
        assert command not in DOCTOR
    assert "does not change your system" in DOCTOR
    for tool in (
        "git",
        "docker",
        "node",
        "corepack",
        "pnpm",
        "python",
        "uv",
        "terraform",
        "aws",
        "jq",
    ):
        assert tool in DOCTOR


def test_seed_is_explicit_and_idempotent() -> None:
    seed_path = REPO_ROOT / "apps" / "api" / "src" / "budgetlens" / "seed.py"
    seed = seed_path.read_text(encoding="utf-8")
    assert "_upsert_user" in seed
    assert "_upsert_org" in seed
    assert "versions.get(version_id)" in seed
    assert "assert_seed_allowed" in seed
    assert "DEMO_SEEDED" in seed
    assert "python -m budgetlens seed" not in ENTRYPOINT.split("api)", 1)[1].split("worker)", 1)[0]


def test_bootstrap_prepares_env_and_storage_without_seeding() -> None:
    assert "cp .env.example .env" in BOOTSTRAP
    assert "uv sync" in BOOTSTRAP
    assert "mkdir -p var/storage" in BOOTSTRAP
    assert "python -m budgetlens seed" not in BOOTSTRAP


def test_reset_local_data_requires_explicit_confirmation() -> None:
    assert "CONFIRM:-" in RESET or "${CONFIRM:-}" in RESET
    assert "CONFIRM=1" in RESET
    assert "down --volumes" in RESET


def test_ide_tasks_and_debug_configs_are_present_without_secrets() -> None:
    tasks_path = REPO_ROOT / ".vscode" / "tasks.json"
    launch_path = REPO_ROOT / ".vscode" / "launch.json"
    settings_path = REPO_ROOT / ".vscode" / "settings.json"
    tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
    launch = json.loads(launch_path.read_text(encoding="utf-8"))
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    labels = {task["label"] for task in tasks["tasks"]}
    assert {"dev", "test", "lint"} <= labels
    names = {config["name"] for config in launch["configurations"]}
    assert "API" in names
    assert "Web" in names
    blob = json.dumps(launch)
    assert "AKIA" not in blob
    assert "BEGIN " not in blob
    assert "password" not in blob.lower()
    assert settings["editor.formatOnSave"] is True
    assert "apps/api/.venv/bin/python" in str(settings["python.defaultInterpreterPath"])
    assert settings["python.testing.pytestEnabled"] is True
    assert settings["typescript.tsdk"] == "node_modules/typescript/lib"


def test_readme_covers_onboarding_and_local_troubleshooting() -> None:
    for token in (
        "make doctor",
        "make bootstrap",
        "make dev",
        "make migrate",
        "make seed",
        "make test",
        "make reset-local-data CONFIRM=1",
        "http://localhost:3000",
        "http://localhost:8000/docs",
        "Docker daemon",
        "Port already allocated",
        "Database volume",
        "Pending migration",
        "Playwright browsers",
        "Local storage permission",
    ):
        assert token in README
