from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
TF_ROOT = REPO_ROOT / "infrastructure" / "terraform"
MODULE_NAMES = (
    "network",
    "security",
    "ecr",
    "database",
    "storage",
    "identity",
    "compute",
    "edge",
    "observability",
    "github_oidc",
)
ENVIRONMENTS = ("dev", "prod")
REQUIRED_TAGS = (
    "Project",
    "Environment",
    "ManagedBy",
    "Owner",
    "CostCenter",
    "DataClassification",
)
REQUIRED_OUTPUTS = (
    "application_url",
    "api_health_url",
    "ecr_repository_url",
    "ecs_cluster_name",
    "ecs_service_name",
    "migration_task_definition_arn",
    "cognito_user_pool_id",
    "cognito_client_id",
    "oidc_issuer",
    "data_bucket_name",
    "app_secret_arn",
    "rds_identifier",
    "dns_validation_records",
    "alarm_topic_arn",
    "dashboard_name",
    "private_subnet_ids",
    "ecs_security_group_id",
    "api_task_definition_arn",
)


def _tf_files() -> list[Path]:
    return [path for path in TF_ROOT.rglob("*.tf") if ".terraform" not in path.parts]


def _read(relative: str) -> str:
    return (TF_ROOT / relative).read_text(encoding="utf-8")


NATIVE_TEST_MODULES = (
    "network",
    "compute",
    "database",
    "identity",
    "storage",
    "github_oidc",
)


def test_module_and_environment_layout_exists() -> None:
    for name in MODULE_NAMES:
        module = TF_ROOT / "modules" / name
        assert (module / "main.tf").is_file(), name
        assert (module / "variables.tf").is_file(), name
        assert (module / "outputs.tf").is_file(), name
        assert (module / "README.md").is_file(), name
    for name in NATIVE_TEST_MODULES:
        tests = list((TF_ROOT / "modules" / name).glob("tests/*.tftest.hcl"))
        assert tests, name
    for environment in ENVIRONMENTS:
        root = TF_ROOT / "environments" / environment
        assert (root / "main.tf").is_file(), environment
        assert (root / "backend.tf").is_file(), environment
        assert (root / "terraform.tfvars").is_file(), environment
        assert (root / "README.md").is_file(), environment
    assert (TF_ROOT / "bootstrap" / "main.tf").is_file()


def test_backends_use_native_lockfile_and_separate_keys() -> None:
    bootstrap = _read("bootstrap/backend.tf")
    dev = _read("environments/dev/backend.tf")
    prod = _read("environments/prod/backend.tf")
    for text in (bootstrap, dev, prod):
        assert "use_lockfile = true" in text
        assert "encrypt      = true" in text
        assert "dynamodb_table" not in text
    assert 'key          = "budgetlens/bootstrap/terraform.tfstate"' in bootstrap
    assert 'key          = "budgetlens/dev/terraform.tfstate"' in dev
    assert 'key          = "budgetlens/prod/terraform.tfstate"' in prod


def test_providers_set_required_tags_and_optional_account_guard() -> None:
    for relative in (
        "bootstrap/providers.tf",
        "environments/dev/providers.tf",
        "environments/prod/providers.tf",
    ):
        text = _read(relative)
        assert "allowed_account_ids" in text
        for tag in REQUIRED_TAGS:
            assert tag in text or tag in _read(relative.replace("providers.tf", "locals.tf"))


def test_task_definitions_reject_latest_and_run_controlled_migrations() -> None:
    compute = _read("modules/compute/main.tf")
    variables = _read("modules/compute/variables.tf")
    assert ":(latest|LATEST)$" in variables
    assert "must not use the latest tag" in variables
    assert '["migrate"]' in compute
    assert 'RUN_MIGRATIONS_ON_START' in compute
    assert '"0"' in compute
    assert "deployment_circuit_breaker" in compute
    assert "GIT_SHA" in compute
    assert "APP_VERSION" in compute
    assert "assign_public_ip = false" in compute
    assert "/api/v1/health/ready" in compute
    assert "secretsmanager" in compute.lower() or "app_secret_arn" in compute
    assert "DataBucketEncryption" in compute
    assert "kms:GenerateDataKey" in compute


def test_network_keeps_rds_private_and_tasks_off_the_internet() -> None:
    network = _read("modules/network/main.tf")
    database = _read("modules/database/main.tf")
    compute = _read("modules/compute/main.tf")
    assert "aws_subnet" in network and "isolated" in network
    assert "publicly_accessible                   = false" in database
    assert "0.0.0.0/0" not in database or "443" in database
    assert 'from_port                    = 5432' in compute
    assert "cloudfront.origin-facing" in compute
    assert "assign_public_ip = false" in compute


def test_storage_is_private_and_state_bucket_is_separate() -> None:
    storage = _read("modules/storage/main.tf")
    bootstrap = _read("bootstrap/main.tf")
    assert "block_public_acls       = true" in storage
    assert "uploads/" in storage
    assert "errors/" in storage
    assert "exports/" in storage
    assert "budgetlens-tfstate-" in bootstrap
    assert "aws_s3_bucket" in bootstrap
    assert "force_destroy = false" in bootstrap
    assert 'sse_algorithm = "AES256"' in storage
    assert "ALBAccessLogsAccount" in storage


def test_identity_is_public_pkce_client_without_users() -> None:
    identity = _read("modules/identity/main.tf")
    assert "generate_secret                               = false" in identity
    assert 'allowed_oauth_flows                           = ["code"]' in identity
    assert "aws_cognito_user" not in identity.replace("aws_cognito_user_pool", "")
    assert "aws_cognito_user_group" not in identity


def test_environment_defaults_match_dev_and_prod_controls() -> None:
    dev = _read("environments/dev/terraform.tfvars")
    prod = _read("environments/prod/terraform.tfvars")
    assert "api_desired_count           = 1" in dev
    assert "db_multi_az                 = false" in dev
    assert "nat_gateway_count           = 1" in dev
    assert "log_retention_days          = 14" in dev
    assert "api_desired_count           = 2" in prod
    assert "db_multi_az                 = true" in prod
    assert "nat_gateway_count           = 2" in prod
    assert "deletion_protection         = true" in prod
    assert "log_retention_days          = 30" in prod
    assert ":latest" not in dev
    assert ":latest" not in prod


def test_environment_outputs_cover_deploy_and_dns() -> None:
    text = _read("environments/dev/outputs.tf")
    for name in REQUIRED_OUTPUTS:
        assert f'output "{name}"' in text, name
    assert "sensitive   = true" in text
    assert "Never the secret value" in text or "never" in text.lower()


def test_terraform_tree_has_no_access_keys_or_passwords() -> None:
    offenders: list[str] = []
    needles = (
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "BEGIN RSA PRIVATE KEY",
        'password = "',
    )
    for path in _tf_files():
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle in text and "random_password" not in text:
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{needle}")
    assert offenders == []
    for path in TF_ROOT.rglob("*.tfvars"):
        text = path.read_text(encoding="utf-8")
        assert "AKIA" not in text
        assert "password" not in text.lower() or "Do not put passwords" in text
    oidc = _read("modules/github_oidc/main.tf")
    assert "ManagePrefixedRoles" in oidc
    assert "iam:CreateRole" in oidc
    assert "token.actions.githubusercontent.com:iss" in oidc
    assert "max_session_duration = 3600" in oidc
    assert "ref:refs/tags/v*" in oidc
    scan = (REPO_ROOT / "scripts" / "scan.sh").read_text(encoding="utf-8")
    assert "terraform test" in scan
