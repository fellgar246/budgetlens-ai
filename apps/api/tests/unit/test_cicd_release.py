from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = REPO_ROOT / "scripts"
WORKFLOWS = REPO_ROOT / ".github" / "workflows"


def _load(name: str) -> ModuleType:
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _workflow(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def test_required_release_workflows_exist() -> None:
    for name in ("ci.yml", "build.yml", "terraform-plan.yml", "deploy-dev.yml", "deploy-prod.yml"):
        assert (WORKFLOWS / name).is_file(), name


def test_workflows_use_oidc_and_never_store_access_keys() -> None:
    offenders: list[str] = []
    for path in (REPO_ROOT / ".github").rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if "AWS_ACCESS_KEY_ID" in text or "AWS_SECRET_ACCESS_KEY" in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == []
    for name in ("build.yml", "terraform-plan.yml", "deploy-dev.yml", "deploy-prod.yml"):
        text = _workflow(name)
        assert "id-token: write" in text
        assert "configure-aws-credentials" in text
        assert "role-to-assume" in text
        assert "role-duration-seconds: 3600" in text


def test_workflows_never_deploy_latest() -> None:
    for name in ("build.yml", "deploy-dev.yml", "deploy-prod.yml"):
        text = _workflow(name)
        assert "ECR_REPOSITORY}:latest" not in text
        assert ":latest }" not in text
        assert "tag: latest" not in text
        assert "latest" in text.lower()
    assert "@sha256:" in _workflow("deploy-dev.yml")
    assert "@sha256:" in _workflow("deploy-prod.yml")
    assert "promote-image.sh" in _workflow("deploy-prod.yml")


def test_ci_has_path_detection_and_required_jobs() -> None:
    text = _workflow("ci.yml")
    assert "ci_changes.py" in text
    for job in (
        "Changeset / path detection",
        "API lint, types, unit, integration",
        "OpenAPI / client drift",
        "Web lint, types, unit, build",
        "E2E smoke",
        "Dependency and secret scan",
        "Terraform fmt, validate, lint, scan",
    ):
        assert job in text


def test_build_publishes_sha_and_optional_semver() -> None:
    text = _workflow("build.yml")
    assert "GIT_SHA" in text
    assert "APP_VERSION" in text
    assert "trivy image" in text
    assert "web-${{ steps.meta.outputs.sha }}" in text
    assert "review_public_env.py" in text
    assert "ECR_REPOSITORY}:${SHA}" in text or "${ECR_REPOSITORY}:${SHA}" in text
    assert "${ECR_REPOSITORY}:${VERSION}" in text


def test_terraform_plan_keeps_plan_file_off_the_log() -> None:
    text = _workflow("terraform-plan.yml")
    assert "PLAN_ROLE_ARN" in text
    assert "terraform-remote.sh" in text
    assert "terraform_plan_guard.py" in text
    assert "record_gate.py" in text
    assert "is not printed" in text
    assert "retention-days: 3" in text
    assert "-auto-approve" not in text


def test_deploy_runs_migration_before_schema_dependent_traffic() -> None:
    for name in ("deploy-dev.yml", "deploy-prod.yml"):
        text = _workflow(name)
        assert "run-migration-task.sh" in text
        assert "smoke-release.sh" in text
        assert "rollback-release.sh" in text
        assert "release_evidence.py" in text
        assert "deploy_preflight.py" in text
        assert "environment: " in text
        migrate_at = text.index("run-migration-task.sh")
        apply_at = text.index('terraform -chdir="${TF_ROOT}" apply')
        assert migrate_at < apply_at or "first apply" in text


def test_prod_requires_protected_environment_backup_and_same_digest() -> None:
    text = _workflow("deploy-prod.yml")
    assert "environment: prod" in text
    assert "create-db-snapshot" in text
    assert "promote-image.sh" in text
    assert 'tags: ["v*.*.*"]' in text or 'tags: ["v*.*.*"]' in text.replace("'", '"')


def test_codeowners_covers_infrastructure_migrations_and_auth() -> None:
    text = (REPO_ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    assert "/infrastructure/" in text
    assert "/apps/api/migrations/" in text
    assert "oidc.py" in text


def test_ci_changes_classifies_paths() -> None:
    changes = _load("ci_changes")
    docs_only = changes.classify_paths(["docs/OPERATIONS.md"])
    assert docs_only["security"] is True
    assert docs_only["api"] is False
    assert docs_only["terraform"] is False
    api = changes.classify_paths(["apps/api/src/budgetlens/config.py"])
    assert api["api"] is True
    assert api["e2e"] is True
    terraform = changes.classify_paths(["infrastructure/terraform/modules/compute/main.tf"])
    assert terraform["terraform"] is True
    assert terraform["web"] is False
    forced = changes.classify_paths([".github/workflows/ci.yml"])
    assert all(forced.values())
    empty = changes.classify_paths([])
    assert all(empty.values())


def test_ci_gate_requires_selected_jobs() -> None:
    changes = _load("ci_changes")
    needs = {
        "changes": {"result": "success"},
        "api": {"result": "success"},
        "security": {"result": "success"},
        "terraform": {"result": "skipped"},
        "web": {"result": "skipped"},
        "contract": {"result": "skipped"},
        "e2e": {"result": "skipped"},
    }
    selected = {
        "api": True,
        "web": False,
        "contract": False,
        "e2e": False,
        "terraform": False,
        "security": True,
    }
    assert changes.evaluate_gate(needs, selected) is True
    needs["api"] = {"result": "failure"}
    assert changes.evaluate_gate(needs, selected) is False


def test_plan_guard_fails_unexpected_destroys_and_redacts_secrets() -> None:
    guard = _load("terraform_plan_guard")
    changes = guard.parse_plan(
        {
            "resource_changes": [
                {
                    "address": "module.database.aws_db_instance.this",
                    "type": "aws_db_instance",
                    "change": {"actions": ["delete"]},
                },
                {
                    "address": "module.edge.aws_cloudfront_distribution.this",
                    "type": "aws_cloudfront_distribution",
                    "change": {"actions": ["update"]},
                },
            ]
        }
    )
    offenders = guard.unexpected_destroys(changes)
    assert any("aws_db_instance" in item for item in offenders)
    assert guard.unexpected_destroys(changes, ["module.database.aws_db_instance.this"]) == []
    redacted = guard.redact(
        {"DATABASE_URL": "postgresql://budgetlens:secret@localhost/db", "name": "ok"}
    )
    assert redacted["DATABASE_URL"] == "(redacted)"
    assert redacted["name"] == "ok"


def test_public_env_review_rejects_secrets() -> None:
    review = _load("review_public_env")
    assert (
        review.review_public_env(
            {"NEXT_PUBLIC_API_BASE_URL": "https://example.com", "NEXT_PUBLIC_APP_ENV": "dev"}
        )
        == []
    )
    assert review.review_public_env({"NEXT_PUBLIC_API_BASE_URL": "AKIAIOSFODNN7EXAMPLE"}) != []
    assert review.review_public_env({"NEXT_PUBLIC_SECRET_TOKEN": "abc"}) != []


def test_release_evidence_requires_digest_identity() -> None:
    evidence = _load("release_evidence")
    payload = evidence.build_evidence(
        commit="abc123",
        image_digest="123.dkr.ecr.us-east-1.amazonaws.com/api@sha256:abcd",
        terraform_plan="approved",
        migration_revision="rev",
        smoke_results="passed",
        ai_evaluation="stub",
        known_risks="R-06",
        rollback_target="arn:task",
    )
    assert set(evidence.REQUIRED_FIELDS) <= set(payload)
    try:
        evidence.build_evidence(
            commit="abc123",
            image_digest="repo:latest",
            terraform_plan="approved",
            migration_revision="rev",
            smoke_results="passed",
            ai_evaluation="stub",
            known_risks="R-06",
            rollback_target="arn:task",
        )
    except ValueError as error:
        assert "latest" in str(error)
    else:
        raise AssertionError("latest digest must be rejected")


def test_changelog_parses_semver_and_commit_subjects() -> None:
    changelog = _load("changelog")
    assert changelog.semver_from_ref("refs/tags/v1.2.3") == "1.2.3"
    subjects = changelog.parse_subjects(
        "abc1234 Add deploy workflow\nfff9999 Merge branch 'main'\n"
    )
    assert subjects == ["Add deploy workflow"]
    text = changelog.render_changelog("1.2.3", subjects)
    assert text.startswith("## 1.2.3")
    assert "Add deploy workflow" in text


def test_release_scripts_exist_and_refuse_latest() -> None:
    for name in (
        "run-migration-task.sh",
        "deploy-web.sh",
        "smoke-release.sh",
        "rollback-release.sh",
        "promote-image.sh",
        "terraform-remote.sh",
        "run-seed-task.sh",
        "restore-test.sh",
        "bootstrap-state.sh",
        "plan-environment.sh",
        "apply-environment.sh",
    ):
        path = SCRIPTS / name
        text = path.read_text(encoding="utf-8")
        assert path.is_file()
        assert text.startswith("#!/bin/sh")
    migrate = (SCRIPTS / "run-migration-task.sh").read_text(encoding="utf-8")
    assert "assignPublicIp=DISABLED" in migrate
    assert "latest" in migrate
    promote = (SCRIPTS / "promote-image.sh").read_text(encoding="utf-8")
    assert "@sha256:" in promote
    rollback = (SCRIPTS / "rollback-release.sh").read_text(encoding="utf-8")
    assert "downgrade" in rollback.lower()
    web = (SCRIPTS / "deploy-web.sh").read_text(encoding="utf-8")
    assert "create-invalidation" in web
    assert "/_next/static" in web or "HTML" in web
    scan = (SCRIPTS / "scan.sh").read_text(encoding="utf-8")
    assert "SCAN_SCOPE" in scan
    assert "scope_enabled" in scan
    assert "sbom" in scan
    assert "var/sbom" in scan
