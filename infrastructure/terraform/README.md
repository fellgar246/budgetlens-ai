# Terraform layout

This tree holds the AWS environments. The local product does not require Terraform.

```text
terraform/
├── bootstrap/       # state bucket and GitHub OIDC bootstrap
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

Do not commit `.tfstate`, `*.tfplan`, or credentials. On AWS, secrets come from Secrets Manager at runtime, not from versioned variables. CI assumes AWS through GitHub OIDC, not permanent access keys.

`make scan` runs `terraform fmt -check`, TFLint, and Checkov when `.tf` files exist and the binaries are installed.
