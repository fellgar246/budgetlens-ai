# security

Creates the environment KMS key (rotation enabled) and an optional CloudFront-scoped WAF web ACL.

WAF stays off until a threat review accepts the cost. The web ACL is associated from the edge module.

## Example

```hcl
module "security" {
  source = "../../modules/security"

  name_prefix = "budgetlens-dev"
  enable_waf  = false
}
```
