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

Do not commit `.tfstate`, `*.tfplan`, or credentials. On AWS, secrets come from Secrets Manager at runtime, not from versioned variables.

`make scan` runs `terraform fmt -check`, TFLint, and Checkov when `.tf` files exist and the binaries are installed.
