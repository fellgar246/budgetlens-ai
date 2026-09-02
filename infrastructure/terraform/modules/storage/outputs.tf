output "web_bucket_id" {
  description = "Private static-web bucket name."
  value       = aws_s3_bucket.web.id
}

output "web_bucket_arn" {
  description = "Private static-web bucket ARN."
  value       = aws_s3_bucket.web.arn
}

output "web_bucket_regional_domain_name" {
  description = "Regional domain name used as the CloudFront S3 origin."
  value       = aws_s3_bucket.web.bucket_regional_domain_name
}

output "data_bucket_id" {
  description = "Application data bucket name."
  value       = aws_s3_bucket.data.id
}

output "data_bucket_arn" {
  description = "Application data bucket ARN."
  value       = aws_s3_bucket.data.arn
}

output "logs_bucket_id" {
  description = "Access-log bucket name, or empty when logging is disabled."
  value       = var.enable_access_logs ? aws_s3_bucket.logs[0].id : ""
}

output "logs_bucket_arn" {
  description = "Access-log bucket ARN, or empty when logging is disabled."
  value       = var.enable_access_logs ? aws_s3_bucket.logs[0].arn : ""
}

output "logs_bucket_domain_name" {
  description = "Access-log bucket domain name used by CloudFront logging."
  value       = var.enable_access_logs ? aws_s3_bucket.logs[0].bucket_domain_name : ""
}
