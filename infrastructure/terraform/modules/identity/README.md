# identity

Creates a Cognito user pool and a public app client for Authorization Code with PKCE. No client secret is generated. Business roles stay in PostgreSQL.

This module does not create users. MFA and self-registration are variables and stay conservative until a human policy decision (M-07). `allow_self_registration` remains false until that gate is recorded.

Callback URLs must be known HTTPS origins. After CloudFront exists, add its URL and apply again if no custom domain was set.

## Example

```hcl
module "identity" {
  source = "../../modules/identity"

  name_prefix             = "budgetlens-dev"
  callback_urls           = ["https://localhost/login"]
  logout_urls             = ["https://localhost/"]
  mfa_configuration       = "OPTIONAL"
  allow_self_registration = false
}
```
