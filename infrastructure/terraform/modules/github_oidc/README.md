# github_oidc

Creates the GitHub Actions OIDC provider and three roles:

- `plan` — ReadOnly plus Terraform state, trusted from main, pull requests, and both GitHub environments
- `deploy-dev` — apply permissions, trusted from main and the `dev` environment
- `deploy-prod` — apply permissions, trusted only from the `prod` environment

IAM role management is limited to `arn:aws:iam::*:role/<name_prefix>-*`. Production apply still requires a human-approved GitHub Environment. No long-lived access keys are created.

## Example

```hcl
module "github_oidc" {
  source = "../../modules/github_oidc"

  name_prefix       = "budgetlens"
  github_owner      = "example"
  github_repository = "budgetlens"
  state_bucket_arn  = aws_s3_bucket.state.arn
}
```
