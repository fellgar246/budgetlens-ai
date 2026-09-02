output "kms_key_arn" {
  description = "Customer-managed KMS key ARN used for logs, secrets, and buckets."
  value       = aws_kms_key.this.arn
}

output "kms_key_id" {
  description = "Customer-managed KMS key ID."
  value       = aws_kms_key.this.key_id
}

output "waf_web_acl_arn" {
  description = "CloudFront WAF web ACL ARN, or empty when WAF is disabled."
  value       = var.enable_waf ? aws_wafv2_web_acl.cloudfront[0].arn : ""
}
