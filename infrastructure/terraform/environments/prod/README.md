# Production environment

Safer defaults: NAT per AZ, two API tasks, Multi-AZ RDS, deletion protection, 30-day logs, and autoscaling. WAF stays off until a threat review.

Do not use Terraform workspaces. The state key is `budgetlens/prod/terraform.tfstate`.

Never run `terraform apply -auto-approve` against this root. Seed tasks are not created. Production apply goes through the protected `prod` GitHub Environment; see [CICD.md](../../../../docs/CICD.md).

## Apply sequence

1. Use a separate AWS account when possible.
2. Record account, region, owner, cost center, and `aws_account_id`.
3. Review `cost_visible_sizes` and record a dated official cost estimate. A budget is an alert, not a hard cap.
4. Review a saved plan, especially destroys and replacements.
5. Run the one-off migration task before shifting traffic to a schema-dependent image.
6. Confirm SNS, budget, and cost-anomaly email subscriptions manually.

Production release still requires backup restore evidence, live AI evaluation when Bedrock is enabled, and the remaining human gates in [GATES.md](../../../../docs/GATES.md), including M-10.
