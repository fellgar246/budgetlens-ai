# edge

Creates a single CloudFront distribution:

- Private S3 origin with Origin Access Control
- `/api/*` to the environment ALB (no cache)
- HTTP to HTTPS redirect
- Compression and a security-headers policy
- Optional ACM certificate and Route 53 records

Development can start on the CloudFront domain. Logging stays off until cost is approved.

## Example

```hcl
module "edge" {
  source = "../../modules/edge"

  providers = {
    aws           = aws
    aws.us_east_1 = aws.us_east_1
  }

  name_prefix                      = "budgetlens-dev"
  web_bucket_id                    = module.storage.web_bucket_id
  web_bucket_arn                   = module.storage.web_bucket_arn
  web_bucket_regional_domain_name  = module.storage.web_bucket_regional_domain_name
  alb_dns_name                     = module.compute.alb_dns_name
  domain_name                      = ""
  create_dns_records               = false
  enable_access_logs               = false
}
```
