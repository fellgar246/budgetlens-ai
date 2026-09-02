output "state_bucket_id" {
  description = "Versioned encrypted S3 bucket used only for Terraform state."
  value       = aws_s3_bucket.state.id
}

output "state_bucket_arn" {
  description = "Terraform state bucket ARN."
  value       = aws_s3_bucket.state.arn
}

output "state_bucket_region" {
  description = "Region of the Terraform state bucket."
  value       = var.aws_region
}

output "github_plan_role_arn" {
  description = "GitHub Actions plan role ARN, or null when GitHub is not configured."
  value       = local.create_oidc ? module.github_oidc[0].plan_role_arn : null
}

output "github_deploy_dev_role_arn" {
  description = "GitHub Actions development deploy role ARN, or null when GitHub is not configured."
  value       = local.create_oidc ? module.github_oidc[0].deploy_dev_role_arn : null
}

output "github_deploy_prod_role_arn" {
  description = "GitHub Actions production deploy role ARN, or null when GitHub is not configured."
  value       = local.create_oidc ? module.github_oidc[0].deploy_prod_role_arn : null
}

output "backend_config_example" {
  description = "Partial backend arguments to pass to environment roots. Does not include credentials."
  value = {
    bucket = aws_s3_bucket.state.id
    region = var.aws_region
  }
}

output "monthly_budget_name" {
  description = "Account budget name when created. A budget is an alert, not a hard cap."
  value       = local.create_budget ? aws_budgets_budget.monthly[0].name : null
}

output "cost_anomaly_monitor_arn" {
  description = "Cost Anomaly Detection monitor ARN when the control is enabled and approved."
  value       = local.create_cost_anomaly ? aws_ce_anomaly_monitor.services[0].arn : null
}

output "aws_account_id" {
  description = "Recorded AWS account ID used to confirm apply and teardown identity."
  value       = var.aws_account_id
}
