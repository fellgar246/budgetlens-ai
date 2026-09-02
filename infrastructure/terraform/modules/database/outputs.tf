output "identifier" {
  description = "RDS instance identifier."
  value       = aws_db_instance.this.id
}

output "endpoint" {
  description = "RDS hostname. Does not include credentials."
  value       = aws_db_instance.this.address
}

output "port" {
  description = "PostgreSQL port."
  value       = aws_db_instance.this.port
}

output "security_group_id" {
  description = "Database security group. Ingress is added by the compute module."
  value       = aws_security_group.rds.id
}

output "app_secret_arn" {
  description = "Secrets Manager ARN that stores DATABASE_URL and STORAGE_KEY_PEPPER. Never the secret value."
  value       = aws_secretsmanager_secret.app.arn
  sensitive   = true
}

output "app_secret_name" {
  description = "Secrets Manager name for the application secret."
  value       = aws_secretsmanager_secret.app.name
}
