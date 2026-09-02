# Development environment

Low-cost AWS layout: one NAT Gateway, one API task, single-AZ RDS, 14-day logs, and no WAF.

Do not use Terraform workspaces to mix this root with production. The state key is `budgetlens/dev/terraform.tfstate`.

## Apply sequence

1. Record the AWS account, region, owner, and cost center. Set `aws_account_id`.
2. Bootstrap remote state if it does not exist.
3. Replace `api_image` with a published digest. The placeholder digest is not deployable.
4. `terraform init -backend=false` for static validation, or `-backend-config=backend.hcl` against the state bucket.
5. Review `terraform plan`. Reject unexpected destroys.
6. Apply only after the human review for this environment.

After the first apply, add the CloudFront URL to `additional_app_urls` so Cognito callbacks and CORS match the distribution.

Migrations run as a one-off ECS task (`migration_task_definition_family`). The API task sets `RUN_MIGRATIONS_ON_START=0`. Seed is a separate task and is never attached to a service.

Bedrock stays disabled (`ai_provider = "stub"`) until model access and live evaluation are complete.
