# storage

Creates the private web bucket, the application data bucket, and an optional access-log bucket. All buckets block public access, require TLS, and use KMS encryption.

The data bucket expires `uploads/`, `errors/`, and `exports/` prefixes to match application retention. CloudFront Origin Access Control is attached by the edge module.

This module never creates the Terraform state bucket.

## Example

```hcl
module "storage" {
  source = "../../modules/storage"

  name_prefix                   = "budgetlens-dev"
  kms_key_arn                   = module.security.kms_key_arn
  enable_web_versioning         = false
  enable_data_versioning        = true
  enable_access_logs            = false
  original_file_retention_days  = 90
  error_report_retention_days   = 30
  export_retention_days         = 1
}
```
