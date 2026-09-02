output "distribution_id" {
  description = "CloudFront distribution ID."
  value       = aws_cloudfront_distribution.this.id
}

output "distribution_arn" {
  description = "CloudFront distribution ARN."
  value       = aws_cloudfront_distribution.this.arn
}

output "distribution_domain_name" {
  description = "CloudFront domain name."
  value       = aws_cloudfront_distribution.this.domain_name
}

output "application_url" {
  description = "HTTPS URL operators should use for the web app."
  value       = var.domain_name == "" ? "https://${aws_cloudfront_distribution.this.domain_name}" : "https://${var.domain_name}"
}

output "api_health_url" {
  description = "Public HTTPS health URL through CloudFront."
  value       = "${var.domain_name == "" ? "https://${aws_cloudfront_distribution.this.domain_name}" : "https://${var.domain_name}"}/api/v1/health/ready"
}

output "acm_certificate_arn" {
  description = "us-east-1 ACM certificate ARN, or null when using the CloudFront default certificate."
  value       = var.domain_name == "" ? null : aws_acm_certificate.cdn[0].arn
}

output "dns_validation_records" {
  description = "ACM DNS validation records to configure outside Route 53."
  value = var.domain_name == "" ? [] : [
    for option in aws_acm_certificate.cdn[0].domain_validation_options : {
      name  = option.resource_record_name
      type  = option.resource_record_type
      value = option.resource_record_value
    }
  ]
}
