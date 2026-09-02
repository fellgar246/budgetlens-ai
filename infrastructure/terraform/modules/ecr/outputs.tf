output "repository_url" {
  description = "API image repository URL."
  value       = aws_ecr_repository.api.repository_url
}

output "repository_arn" {
  description = "API image repository ARN."
  value       = aws_ecr_repository.api.arn
}

output "repository_name" {
  description = "API image repository name."
  value       = aws_ecr_repository.api.name
}
