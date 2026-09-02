# storage

Creates the private web bucket, the application data bucket, and an optional access-log bucket. Application buckets block public access, require TLS, and use KMS encryption. The access-log bucket uses SSE-S3 because ALB delivery does not support a customer KMS key.

The data bucket expires `uploads/`, `errors/`, and `exports/` prefixes to match application retention. This module does not write the web bucket policy; the edge module attaches Origin Access Control as a dependency contract. Buckets set `force_destroy = false` so destroy does not empty objects by itself.

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
