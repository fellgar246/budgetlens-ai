output "sns_topic_arn" {
  description = "SNS topic ARN for operational alarms. Email confirmation is manual."
  value       = aws_sns_topic.alarms.arn
}

output "dashboard_name" {
  description = "CloudWatch dashboard name. The dashboard does not include financial amounts."
  value       = aws_cloudwatch_dashboard.ops.dashboard_name
}
