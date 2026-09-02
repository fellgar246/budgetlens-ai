from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from budgetlens.seed import (
    ALLOWED_SEED_ENVIRONMENTS,
    DEMO_ORGANIZATION_SLUGS,
    DEMO_USER_EMAILS,
    assert_seed_allowed,
    demo_dataset_label,
    run_seed,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = REPO_ROOT / "scripts"
DOCS = REPO_ROOT / "docs"
WORKFLOWS = REPO_ROOT / ".github" / "workflows"


def _load(name: str) -> ModuleType:
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_deployment_document_lists_every_runbook_section() -> None:
    text = (DOCS / "DEPLOYMENT.md").read_text(encoding="utf-8")
    for heading in (
        "## 1. Preflight",
        "## 2. Bootstrap state and OIDC",
        "## 3. Environment plan",
        "## 4. Apply base infrastructure",
        "## 5. Migration",
        "## 6. Application deploy",
        "## 7. Smoke tests",
        "## 8. Demo seed",
        "## 9. Post-deploy observation",
        "## 10. Rollback",
        "## 11. Restore test",
        "## 12. Development teardown",
    ):
        assert heading in text, heading
    assert "never `terraform apply -auto-approve`" in text or "never `-auto-approve`" in text
    assert "budgetlens-dev-restore" in text
    assert "APP_ENV=prod" in text
    assert ("spec" + "-docs") not in text


def test_preflight_requires_digest_identity_and_https() -> None:
    preflight = _load("deploy_preflight")
    digest = "123.dkr.ecr.us-east-1.amazonaws.com/api@sha256:" + ("ab" * 32)
    result = preflight.evaluate_preflight(
        environment="dev",
        image_digest=digest,
        frontend_artifact="built",
        openapi_snapshot=str(REPO_ROOT / "packages" / "api-client" / "openapi.json"),
        ci_status="green",
        aws_account="123456789012",
        aws_role="github-deploy-dev",
        aws_region="us-east-1",
        ai_provider="stub",
        migration_reviewed=True,
        budget_reviewed=True,
        backup_reviewed=True,
    )
    assert result["ok"] is True
    with pytest.raises(ValueError, match="latest"):
        preflight.reject_latest_digest("repo:latest")
    assert preflight.application_uses_https("https://d111.cloudfront.net") is True
    assert preflight.application_uses_https("http://example.com") is False
    failed = preflight.evaluate_preflight(environment="dev", image_digest="repo:latest")
    assert failed["ok"] is False
    assert preflight.main(["--print-checklist"]) == 0


def test_verify_infrastructure_rejects_public_rds_and_missing_outputs() -> None:
    verify = _load("verify_infrastructure")
    outputs = verify.flatten_outputs(
        {
            "environment": {"value": "dev"},
            "aws_account_id": {"value": "123456789012"},
            "application_url": {"value": "https://d111.cloudfront.net"},
            "cloudfront_distribution_id": {"value": "E123"},
            "api_health_url": {"value": "https://d111.cloudfront.net/api/v1/health/ready"},
            "ecr_repository_url": {"value": "123.dkr.ecr.us-east-1.amazonaws.com/api"},
            "ecs_cluster_name": {"value": "budgetlens-dev"},
            "ecs_service_name": {"value": "budgetlens-dev-api"},
            "data_bucket_name": {"value": "budgetlens-dev-data"},
            "web_bucket_name": {"value": "budgetlens-dev-web"},
            "rds_identifier": {"value": "budgetlens-dev"},
            "cognito_user_pool_id": {"value": "us-east-1_abc"},
            "private_subnet_ids": {"value": ["subnet-a", "subnet-b"]},
            "ecs_security_group_id": {"value": "sg-1"},
            "app_secret_arn": {
                "value": "arn:aws:secretsmanager:us-east-1:123:secret:x",
                "sensitive": True,
            },
        }
    )
    assert outputs["app_secret_arn"] == "(redacted)"
    missing = verify.check_outputs(
        outputs, expected_environment="dev", expected_account="123456789012"
    )
    assert missing == []
    assert verify.check_facts(
        {
            "rds_publicly_accessible": True,
            "data_bucket_public": False,
            "web_bucket_public": False,
            "vpc_id": "vpc-1",
            "private_subnet_ids": ["subnet-a", "subnet-b"],
            "ecs_security_group_id": "sg-1",
            "ecr_repository_url": "repo",
            "ecs_cluster_name": "cluster",
            "alb_arn": "arn",
            "log_group_name": "logs",
            "cognito_user_pool_id": "pool",
            "cloudfront_distribution_id": "E123",
        }
    ) == ["RDS must not be publicly accessible"]


def test_smoke_rejects_secrets_and_requires_https_and_trace_id() -> None:
    smoke = _load("smoke_release")
    result = smoke.evaluate_public_smoke(
        application_url="https://d111.cloudfront.net",
        live={"status": "ok"},
        ready={"status": "ready", "components": {"database": "ok"}},
        version={"version": "0.1.0", "commit": "abc1234", "build_time": "2026-09-01T00:00:00Z"},
        headers={"X-Trace-Id": "trace-1"},
        expected_commit="abc1234",
        bodies=['{"status":"ready"}'],
    )
    assert result["health_ready"] == "passed"
    with pytest.raises(ValueError, match="HTTPS"):
        smoke.evaluate_public_smoke(
            application_url="http://example.com",
            live={"status": "ok"},
            ready={"status": "ready"},
            version={"commit": "abc1234"},
            headers={"X-Trace-Id": "trace-1"},
        )
    with pytest.raises(ValueError, match="secret"):
        smoke.reject_secrets("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.abc")
    auth = smoke.evaluate_authenticated_smoke(
        organizations=[{"id": "alpha"}],
        dashboard={"totals": {}},
        variance={"items": []},
        cross_tenant_status=403,
        copilot=None,
        ai_provider="stub",
    )
    assert auth["cross_tenant_negative"] == "403"
    assert "CloudFront or web loads over HTTPS" in smoke.render_checklist()


def test_observation_and_restore_guards() -> None:
    observe = _load("observe_release")
    record = observe.build_observation(
        environment="dev",
        recorded_by="Luis",
        window="2h",
        notes={"api_5xx_latency": "quiet"},
        recorded_at="2026-09-01",
    )
    assert record["items"]
    with pytest.raises(ValueError, match="human"):
        observe.build_observation(environment="dev", recorded_by="agent", window="2h")
    restore = _load("restore_test")
    assert restore.isolated_restore_name("dev") == "budgetlens-dev-restore"
    with pytest.raises(ValueError, match="development"):
        restore.isolated_restore_name("prod")
    restore.refuse_production_traffic(
        "https://app.example",
        "budgetlens-dev-restore.xxxx.rds.amazonaws.com",
    )
    with pytest.raises(ValueError, match="traffic"):
        restore.refuse_production_traffic("https://app.example", "https://app.example")
    errors = restore.review_restore_facts(
        {
            "identifier": "budgetlens-dev-restore",
            "publicly_accessible": False,
            "points_traffic": False,
            "schema_ok": True,
            "counts_ok": True,
            "rpo_observed": "24h",
            "rto_observed": "90m",
        }
    )
    assert errors == []
    assert restore.main(["--print-checklist"]) == 0
    assert observe.main(["--print-checklist"]) == 0


def test_seed_refuses_production_and_keeps_known_demo_tenants() -> None:
    assert_seed_allowed("local")
    assert_seed_allowed("test")
    assert_seed_allowed("dev")
    with pytest.raises(ValueError, match="production"):
        assert_seed_allowed("prod")
    assert demo_dataset_label("dev") == "synthetic-demo"
    assert DEMO_ORGANIZATION_SLUGS == {"alpha", "beta"}
    assert "alex.admin@alpha.local" in DEMO_USER_EMAILS
    assert ALLOWED_SEED_ENVIRONMENTS == {"local", "test", "dev"}


def test_run_seed_refuses_prod_before_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "budgetlens.seed.get_settings",
        lambda: type("Settings", (), {"app_env": "prod"})(),
    )

    def fail_session() -> None:
        raise AssertionError("production seed must not open a database session")

    monkeypatch.setattr("budgetlens.seed.session_scope", fail_session)
    with pytest.raises(ValueError, match="production"):
        run_seed()


def test_runbook_scripts_enforce_confirmation_and_refuse_latest() -> None:
    for name in (
        "bootstrap-state.sh",
        "plan-environment.sh",
        "apply-environment.sh",
        "verify-infrastructure.sh",
        "run-seed-task.sh",
        "restore-test.sh",
        "smoke-release.sh",
        "rollback-release.sh",
        "teardown-environment.sh",
        "deploy-web.sh",
        "run-migration-task.sh",
    ):
        path = SCRIPTS / name
        text = path.read_text(encoding="utf-8")
        assert path.is_file(), name
        assert text.startswith("#!/bin/sh")
    apply = (SCRIPTS / "apply-environment.sh").read_text(encoding="utf-8")
    assert "CONFIRM" in apply
    assert "apply -auto-approve" not in apply
    assert "CONFIRM_PROD" in apply
    bootstrap = (SCRIPTS / "bootstrap-state.sh").read_text(encoding="utf-8")
    assert "backend=false" in bootstrap
    assert "Do not add state" in bootstrap or "stay out of Git" in bootstrap
    seed = (SCRIPTS / "run-seed-task.sh").read_text(encoding="utf-8")
    assert "ENVIRONMENT" in seed
    assert "prod" in seed
    assert "assignPublicIp=DISABLED" in seed
    restore = (SCRIPTS / "restore-test.sh").read_text(encoding="utf-8")
    assert "budgetlens-dev-restore" in restore
    assert "DELETE_RESTORE" in restore
    assert "CONFIRM" in restore
    rollback = (SCRIPTS / "rollback-release.sh").read_text(encoding="utf-8")
    assert "services-stable" in rollback
    assert "downgrade" in rollback.lower()
    web = (SCRIPTS / "deploy-web.sh").read_text(encoding="utf-8")
    assert "max-age=31536000" in web
    assert "manifest" in web
    plan = (SCRIPTS / "plan-environment.sh").read_text(encoding="utf-8")
    assert "terraform_plan_guard.py" in plan
    assert "not applied" in plan or "experiment" in plan


def test_workflows_follow_runbook_order_and_never_auto_seed() -> None:
    for name in ("deploy-dev.yml", "deploy-prod.yml"):
        text = (WORKFLOWS / name).read_text(encoding="utf-8")
        assert "deploy_preflight.py" in text
        assert "verify_infrastructure.py" in text
        assert "observe_release.py" in text
        assert "smoke-release.sh" in text
        assert "run-seed-task.sh" not in text
        assert "apply -auto-approve" not in text
    plan = (WORKFLOWS / "terraform-plan.yml").read_text(encoding="utf-8")
    assert "not applied to experiment" in plan
    prod_main = REPO_ROOT / "infrastructure" / "terraform" / "environments" / "prod" / "main.tf"
    prod = prod_main.read_text(encoding="utf-8")
    assert "create_seed_task          = false" in prod
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    for target in (
        "preflight-deploy",
        "verify-infra",
        "smoke-release",
        "seed-demo",
        "observe-release",
        "restore-test",
        "rollback-release",
    ):
        assert target in makefile
