# compute

Creates the ECS Fargate cluster, API service, ALB, and one-off task definitions.

- API desired count is 1 in development and 2 or more in production
- Deployments use a circuit breaker with rollback
- Secrets are injected from Secrets Manager by ARN and JSON key
- Images must not use the `latest` tag
- Migrations run as `migrate`, never on every API replica
- The same image can run `watchdog`, `retain-files`, `import-job`, or `seed`

The ALB accepts HTTP only from the CloudFront managed prefix list. Browsers reach TLS at CloudFront.

## Example

```hcl
module "compute" {
  source = "../../modules/compute"

  name_prefix         = "budgetlens-dev"
  environment         = "dev"
  api_image           = "111111111111.dkr.ecr.us-east-1.amazonaws.com/budgetlens-dev-api@sha256:..."
  api_cpu             = 256
  api_memory          = 512
  api_desired_count   = 1
  enable_autoscaling  = false
  create_seed_task    = true
}
```
