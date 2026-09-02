# Cost and deployment summary

Dated: 2026-09-01. This page lists Terraform-visible sizes and operational facts. It is not a quote, invoice, or promise.

Do not invent a monthly price. Record a human figure from the official [AWS Pricing Calculator](https://calculator.aws/) or the AWS Price List before the first apply:

```text
python scripts/record_cost_estimate.py --print-sizes --environment dev
make record-cost-estimate ENVIRONMENT=dev SOURCE='https://calculator.aws/#…' MONTHLY_ESTIMATE='<human figure>'
```

No official calculator result is stored in this repository as of 2026-09-01. Until one is recorded, treat AWS spend as unknown.

## Development sizes encoded in Terraform

These values come from `infrastructure/terraform/environments/dev/terraform.tfvars` on 2026-09-01. If they change, print sizes again and record a new estimate.

| Visible size | Development value |
|---|---|
| `nat_gateway_count` | 1 |
| `api_desired_count` | 1 |
| `api_cpu` | 256 |
| `api_memory` | 512 |
| `db_instance_class` | `db.t4g.micro` |
| `db_allocated_storage` | 20 |
| `db_multi_az` | false |
| `log_retention_days` | 14 |
| `enable_autoscaling` | false |
| `backup_retention_days` | 7 |
| `price_class` | `PriceClass_100` |
| `ai_provider` | `stub` |

WAF, interface endpoints, Container Insights, and access logs stay off in development. Bedrock is not enabled until a human records model access.

`max_monthly_budget` in the same file is a **budget alert threshold** (default 50 in the development tfvars). A budget is an alert, not a hard cap, and not a measured bill.

## What is deployed today

| Surface | Status on 2026-09-01 |
|---|---|
| Local Compose (web, API, PostgreSQL) | Documented and covered by AC-001 |
| Terraform modules and environment roots | Present; `fmt` / validate / TFLint / Checkov in CI |
| GitHub OIDC workflows | Present; disabled until repository variables and environments exist (M-05) |
| AWS development apply | Not performed in this repository; blocked by M-01–M-09 |
| AWS production apply | Blocked by the `prod` gate set including M-10 |
| Public production URL | Not claimed |
| Application tag `v1.0.0` | Not cut; see [RELEASE.md](RELEASE.md) |

If a development environment is later applied and then torn down, keep only secret-free evidence (commit, digest, dated estimate, smoke notes). Follow [DEPLOYMENT.md](DEPLOYMENT.md) and [OPERATIONS.md](OPERATIONS.md#teardown). Destroying unused development is the cost control; leaving it up as a demo requires measuring the real bill for a week before changing sizes.

## Principal cost drivers (no dollar amounts)

| Driver | Control |
|---|---|
| NAT Gateway | One in development; tear down unused environments |
| RDS | Small single-AZ instance in development |
| ECS Fargate | Desired count 1 in development |
| ALB and CloudFront | One pair per environment; cache only static web |
| S3 | Lifecycle on uploads, error reports, and exports |
| CloudWatch | Short development retention; sanitized logs |
| Bedrock | Keep `ai_provider=stub` until live eval is approved |
| Cognito | Self-registration stays off |

## Related runbooks

- [OPERATIONS.md](OPERATIONS.md) — daily checklist, rollback, restore, teardown
- [DEPLOYMENT.md](DEPLOYMENT.md) — ordered AWS apply
- [CICD.md](CICD.md) — OIDC and image digest identity
- [GATES.md](GATES.md) — human decisions the code must not assume
