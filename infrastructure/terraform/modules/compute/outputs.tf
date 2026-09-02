output "cluster_name" {
  description = "ECS cluster name."
  value       = aws_ecs_cluster.this.name
}

output "cluster_arn" {
  description = "ECS cluster ARN."
  value       = aws_ecs_cluster.this.arn
}

output "service_name" {
  description = "API ECS service name."
  value       = aws_ecs_service.api.name
}

output "alb_arn" {
  description = "Application Load Balancer ARN."
  value       = aws_lb.api.arn
}

output "alb_arn_suffix" {
  description = "ALB ARN suffix used by CloudWatch metrics."
  value       = aws_lb.api.arn_suffix
}

output "alb_dns_name" {
  description = "ALB DNS name used as the CloudFront API origin."
  value       = aws_lb.api.dns_name
}

output "alb_security_group_id" {
  description = "ALB security group ID."
  value       = aws_security_group.alb.id
}

output "ecs_security_group_id" {
  description = "ECS task security group ID."
  value       = aws_security_group.ecs.id
}

output "api_task_definition_arn" {
  description = "API task definition ARN."
  value       = aws_ecs_task_definition.api.arn
}

output "migration_task_definition_arn" {
  description = "One-off migration task definition ARN."
  value       = aws_ecs_task_definition.migrate.arn
}

output "migration_task_definition_family" {
  description = "One-off migration task family name."
  value       = aws_ecs_task_definition.migrate.family
}

output "ops_task_definition_arn" {
  description = "Operations task definition ARN used for watchdog, retain-files, or import-job overrides."
  value       = aws_ecs_task_definition.ops.arn
}

output "seed_task_definition_arn" {
  description = "Explicit seed task definition ARN, or null in production."
  value       = var.create_seed_task ? aws_ecs_task_definition.seed[0].arn : null
}

output "execution_role_arn" {
  description = "ECS execution role ARN."
  value       = aws_iam_role.execution.arn
}

output "task_role_arn" {
  description = "ECS task role ARN."
  value       = aws_iam_role.task.arn
}

output "migration_role_arn" {
  description = "ECS migration task role ARN."
  value       = aws_iam_role.migration.arn
}

output "log_group_name" {
  description = "API CloudWatch log group name."
  value       = aws_cloudwatch_log_group.api.name
}

output "health_path" {
  description = "Load balancer health check path."
  value       = "/api/v1/health/ready"
}
