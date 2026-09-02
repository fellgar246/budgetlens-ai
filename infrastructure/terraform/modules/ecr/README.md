# ecr

Creates the API container repository with immutable tags, scan-on-push, and KMS encryption.

Deployments must reference a digest or an immutable tag. The `latest` tag is rejected by environment validation.

## Example

```hcl
module "ecr" {
  source = "../../modules/ecr"

  name_prefix = "budgetlens-dev"
  kms_key_arn = module.security.kms_key_arn
}
```
