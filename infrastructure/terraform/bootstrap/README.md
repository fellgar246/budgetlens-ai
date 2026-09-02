# bootstrap

Creates the remote Terraform state bucket and, when a GitHub repository is provided, the OIDC provider and CI roles. This bucket is never an application data or web bucket.

When `max_monthly_budget` and `alarm_email` are set, bootstrap also creates the account AWS Budget. Chosen actual and forecast percent alerts notify that email. Confirm the subscription manually (M-03). A budget is an alert, not a hard cap.

Record the account (M-01) and primary region (M-02) before this first apply. Leave `aws_account_id` empty in the committed example until a human records the account. Never paste secret keys.

Cost Anomaly Detection and Cost Explorer allocation tags stay off until Cost Explorer is enabled and `enable_cost_anomaly_detection` / `enable_cost_allocation_tags` are approved.

## First apply

The backend block is partial. The first apply uses a local backend:

```text
terraform init -backend=false
terraform plan -var-file=terraform.tfvars
```

After review, apply with temporary administrative credentials. Then migrate state:

```text
cp backend.hcl.example backend.hcl
# set bucket and region from the outputs
terraform init -backend-config=backend.hcl
```

Do not commit `backend.hcl`, `*.tfstate`, or plan files. The first-time command sequence is `scripts/bootstrap-state.sh` in [DEPLOYMENT.md](../../../docs/DEPLOYMENT.md#2-bootstrap-state-and-oidc).

## Outputs used by environment roots

Environment roots take the same bucket and region through `-backend-config`. State keys are:

- `budgetlens/bootstrap/terraform.tfstate`
- `budgetlens/dev/terraform.tfstate`
- `budgetlens/prod/terraform.tfstate`

Native S3 lockfiles are used. Do not create a DynamoDB lock table.
