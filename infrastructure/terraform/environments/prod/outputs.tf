output "environment" {
  description = "Environment name. Confirm this against AWS identity before apply or teardown."
  value       = var.environment
}

output "aws_account_id" {
  description = "Recorded AWS account ID. Confirm it matches the caller identity before apply or teardown."
  value       = var.aws_account_id
}

output "monthly_budget_target_usd" {
  description = "Documented monthly cost target for this environment. A budget is an alert, not a hard cap."
  value       = var.max_monthly_budget
}

output "cost_visible_sizes" {
  description = "Sizes and counts that drive cost. Review before apply. This output is not a price."
  value       = local.cost_visible_sizes
}

output "deletion_protection" {
  description = "Whether RDS and ALB deletion protection is enabled. Disable only through the teardown runbook."
  value       = var.deletion_protection
}

output "application_url" {
  description = "HTTPS URL for the web application."
  value       = module.edge.application_url
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain."
  value       = module.edge.distribution_domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID used for selective invalidations."
  value       = module.edge.distribution_id
}

output "api_health_url" {
  description = "Public HTTPS readiness URL. Does not include credentials."
  value       = module.edge.api_health_url
}

output "ecr_repository_url" {
  description = "API ECR repository URL."
  value       = module.ecr.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name."
  value       = module.compute.cluster_name
}

output "ecs_service_name" {
  description = "API ECS service name."
  value       = module.compute.service_name
}

output "migration_task_definition_arn" {
  description = "One-off migration task definition ARN."
  value       = module.compute.migration_task_definition_arn
}

output "migration_task_definition_family" {
  description = "One-off migration task family."
  value       = module.compute.migration_task_definition_family
}

output "seed_task_definition_arn" {
  description = "Explicit seed task definition. Invoke only in development, never from a service."
  value       = module.compute.seed_task_definition_arn
}

output "cognito_user_pool_id" {
  description = "Cognito user pool ID."
  value       = module.identity.user_pool_id
}

output "cognito_client_id" {
  description = "Public Cognito app client ID. This is not a secret."
  value       = module.identity.client_id
}

output "oidc_issuer" {
  description = "OIDC issuer URL."
  value       = module.identity.issuer
}

output "oidc_jwks_url" {
  description = "OIDC JWKS URL."
  value       = module.identity.jwks_url
}

output "cognito_hosted_ui_domain" {
  description = "Cognito hosted UI domain."
  value       = module.identity.hosted_ui_domain
}

output "data_bucket_name" {
  description = "Application data bucket name."
  value       = module.storage.data_bucket_id
}

output "web_bucket_name" {
  description = "Private static-web bucket name."
  value       = module.storage.web_bucket_id
}

output "app_secret_arn" {
  description = "Secrets Manager ARN. Never the secret value."
  value       = module.database.app_secret_arn
  sensitive   = true
}

output "rds_identifier" {
  description = "RDS instance identifier. The password is not an output."
  value       = module.database.identifier
}

output "dns_validation_records" {
  description = "ACM DNS validation records when Route 53 is not managing the domain."
  value       = module.edge.dns_validation_records
}

output "alarm_topic_arn" {
  description = "SNS topic for operational alarms."
  value       = module.observability.sns_topic_arn
}

output "dashboard_name" {
  description = "CloudWatch dashboard name."
  value       = module.observability.dashboard_name
}

output "private_subnet_ids" {
  description = "Private subnet IDs used to run the one-off migration task."
  value       = module.network.private_subnet_ids
}

output "ecs_security_group_id" {
  description = "ECS task security group used by the one-off migration task."
  value       = module.compute.ecs_security_group_id
}

output "api_task_definition_arn" {
  description = "Current API task definition ARN, used as a rollback target."
  value       = module.compute.api_task_definition_arn
}
