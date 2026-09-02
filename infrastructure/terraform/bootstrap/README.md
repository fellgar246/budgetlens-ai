# bootstrap

Creates the remote Terraform state bucket and, when a GitHub repository is provided, the OIDC provider and CI roles. This bucket is never an application data or web bucket.

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

Do not commit `backend.hcl`, `*.tfstate`, or plan files.

## Outputs used by environment roots

Environment roots take the same bucket and region through `-backend-config`. State keys are:

- `budgetlens/bootstrap/terraform.tfstate`
- `budgetlens/dev/terraform.tfstate`
- `budgetlens/prod/terraform.tfstate`

Native S3 lockfiles are used. Do not create a DynamoDB lock table.
