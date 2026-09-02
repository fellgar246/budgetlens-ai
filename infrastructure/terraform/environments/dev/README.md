# Development environment

Low-cost AWS layout: one NAT Gateway, one API task, single-AZ RDS, 14-day logs, and no WAF.

Do not use Terraform workspaces to mix this root with production. The state key is `budgetlens/dev/terraform.tfstate`.

## Apply sequence

1. Record the AWS account, region, owner, and cost center (M-01, M-02). Set `aws_account_id`.
2. Bootstrap remote state if it does not exist.
3. Review `cost_visible_sizes` and record a dated official cost estimate (`scripts/record_cost_estimate.py`). Do not invent a price (M-03).
4. Replace `api_image` with a published digest. The placeholder digest is not deployable.
5. `terraform init -backend=false` for static validation, or `-backend-config=backend.hcl` against the state bucket.
6. Review `terraform plan`. Reject unexpected destroys.
7. Complete the apply review (M-09) with `make review-apply CONFIRM=1`, or through the `Deploy dev` workflow in [CICD.md](../../../../docs/CICD.md). Confirm the alarm email manually. See [GATES.md](../../../../docs/GATES.md).

Destroy unused development with [teardown](../../../../docs/OPERATIONS.md#teardown). If the environment stays as a portfolio demo, measure the real monthly cost for one week before changing sizes.

After the first apply, add the CloudFront URL to `additional_app_urls` so Cognito callbacks and CORS match the distribution.

Migrations run as a one-off ECS task (`migration_task_definition_family`). The API task sets `RUN_MIGRATIONS_ON_START=0`. Seed is a separate task and is never attached to a service.

Bedrock stays disabled (`ai_provider = "stub"`) until model access and live evaluation are complete.
