# github_oidc

Creates the GitHub Actions OIDC provider and three roles:

- `plan` — ReadOnly plus Terraform state, trusted from main, `v*` tags, pull requests, and both GitHub environments
- `deploy-dev` — apply and image-publish permissions, trusted from main, `v*` tags, and the `dev` environment
- `deploy-prod` — apply permissions, trusted only from the `prod` environment

Trust requires the GitHub issuer and `sts.amazonaws.com` audience. Sessions last at most one hour. IAM role management is limited to `arn:aws:iam::*:role/<name_prefix>-*`. Production apply still requires a human-approved GitHub Environment. No long-lived access keys are created.

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
