# Terraform layout

This tree holds the AWS environments. The local product does not require Terraform.

```text
terraform/
├── bootstrap/       # state bucket, optional GitHub OIDC, account budget and cost alerts
├── modules/         # reusable infrastructure modules
└── environments/    # per-environment roots (dev, prod)
```

Pinned tools:

| Tool | Pin | File |
|---|---|---|
| Terraform | 1.13.5 | `.terraform-version` |
| TFLint | 0.64.0 | `.tflint-version` |
| Checkov | 3.3.9 | `.checkov-version` |

State lives in a versioned, encrypted S3 bucket with `use_lockfile = true`. Do not create a new DynamoDB table for locking. Terraform 1.10 or newer is required; this repository pins 1.13.5.

If a previous root still sets `dynamodb_table`:

1. Upgrade Terraform to the pinned version.
2. Add `use_lockfile = true` beside the existing DynamoDB argument and apply once.
3. Remove `dynamodb_table` and the lock table in a later change.

Do not commit `.tfstate`, `*.tfplan`, `backend.hcl`, or credentials. On AWS, secrets come from Secrets Manager at runtime, not from versioned variables. CI assumes AWS through GitHub OIDC, not permanent access keys.

`make scan` runs `terraform fmt -check -recursive`, `terraform validate` on each root, native `terraform test` on modules that declare tests, TFLint, and Checkov when the binaries are installed.

## Environments

Do not use Terraform workspaces to mix environments. Each root has its own state key and variables:

| Root | State key | Intent |
|---|---|---|
| `bootstrap/` | `budgetlens/bootstrap/terraform.tfstate` | State bucket and CI roles |
| `environments/dev/` | `budgetlens/dev/terraform.tfstate` | Low-cost demonstration |
| `environments/prod/` | `budgetlens/prod/terraform.tfstate` | Safer defaults; apply is never auto-approved |

Static validation does not need AWS credentials:

```text
terraform -chdir=infrastructure/terraform fmt -check -recursive
terraform -chdir=infrastructure/terraform/environments/dev init -backend=false
terraform -chdir=infrastructure/terraform/environments/dev validate
terraform -chdir=infrastructure/terraform/modules/network test
```

A real plan or apply needs a recorded account ID, a published image digest, a dated official cost estimate, and the human gates in [GATES.md](../../docs/GATES.md). Terraform exposes sizes and counts on `cost_visible_sizes`; it does not invent a monthly price. A budget is an alert, not a hard cap.

```text
python scripts/record_cost_estimate.py --print-sizes --environment dev
make record-cost-estimate ENVIRONMENT=dev SOURCE='https://calculator.aws/#...' MONTHLY_ESTIMATE='<human figure>'
```

GitHub Actions run `terraform-plan`, `deploy-dev`, and `deploy-prod` through OIDC as described in [CICD.md](../../docs/CICD.md). Plan files stay off the job log; unexpected destroys fail the guard and are never applied to experiment. The ordered apply runbook is [DEPLOYMENT.md](../../docs/DEPLOYMENT.md). Environment teardown is `scripts/teardown-environment.sh` and never deletes the state bucket.
