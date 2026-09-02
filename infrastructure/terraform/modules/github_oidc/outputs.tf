output "provider_arn" {
  description = "GitHub OIDC provider ARN."
  value       = local.provider_arn
}

output "plan_role_arn" {
  description = "Read-mostly role for terraform plan."
  value       = aws_iam_role.plan.arn
}

output "deploy_dev_role_arn" {
  description = "Deploy role restricted to main and the GitHub environment named dev."
  value       = aws_iam_role.deploy_dev.arn
}

output "deploy_prod_role_arn" {
  description = "Deploy role restricted to the GitHub environment named prod."
  value       = aws_iam_role.deploy_prod.arn
}
