variable "project_name" {
  type        = string
  description = "Project name used in resource names."
  nullable    = false
  default     = "budgetlens"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,20}[a-z0-9]$", var.project_name))
    error_message = "project_name must be a short lowercase DNS label."
  }
}

variable "environment" {
  type        = string
  description = "Environment name. This root is production."
  nullable    = false
  default     = "prod"

  validation {
    condition     = var.environment == "prod"
    error_message = "The production root must set environment=prod. Do not use workspaces to mix environments."
  }
}

variable "aws_region" {
  type        = string
  description = "Primary AWS region for this environment."
  nullable    = false
}

variable "aws_account_id" {
  type        = string
  description = "Twelve-digit AWS account ID. Empty disables allowed_account_ids until the account is recorded."
  nullable    = false
  default     = ""

  validation {
    condition     = var.aws_account_id == "" || can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "aws_account_id must be empty or a 12-digit account ID."
  }
}

variable "owner" {
  type        = string
  description = "Owner tag value."
  nullable    = false
}

variable "cost_center" {
  type        = string
  description = "CostCenter tag value."
  nullable    = false
}

variable "data_classification" {
  type        = string
  description = "DataClassification tag. Production uses financial."
  nullable    = false
  default     = "financial"

  validation {
    condition     = contains(["financial-demo", "financial"], var.data_classification)
    error_message = "data_classification must be financial-demo or financial."
  }
}

variable "vpc_cidr" {
  type        = string
  description = "VPC CIDR. Keep environments unique if they share an account."
  nullable    = false
}

variable "availability_zone_count" {
  type        = number
  description = "Number of Availability Zones. Must be at least 2."
  nullable    = false
  default     = 2
}

variable "nat_gateway_count" {
  type        = number
  description = "NAT Gateways. Development uses 1 to reduce cost."
  nullable    = false
  default     = 1
}

variable "enable_vpc_flow_logs" {
  type        = bool
  description = "Enable VPC flow logs."
  nullable    = false
  default     = false
}

variable "enable_interface_endpoints" {
  type        = bool
  description = "Create interface VPC endpoints. Alternative to extra NAT Gateways."
  nullable    = false
  default     = false
}

variable "enable_waf" {
  type        = bool
  description = "Create a CloudFront WAF web ACL."
  nullable    = false
  default     = false
}

variable "api_cpu" {
  type        = number
  description = "Fargate CPU units for the API task."
  nullable    = false
}

variable "api_memory" {
  type        = number
  description = "Fargate memory in MiB for the API task."
  nullable    = false
}

variable "api_desired_count" {
  type        = number
  description = "Desired API tasks. Development uses 1."
  nullable    = false
}

variable "api_image" {
  type        = string
  description = "API image URI with an immutable tag or digest. Never latest."
  nullable    = false
}

variable "enable_autoscaling" {
  type        = bool
  description = "Enable ECS autoscaling."
  nullable    = false
  default     = false
}

variable "autoscaling_max_count" {
  type        = number
  description = "Maximum API tasks when autoscaling is enabled."
  nullable    = false
  default     = 2
}

variable "db_instance_class" {
  type        = string
  description = "RDS instance class."
  nullable    = false
}

variable "db_allocated_storage" {
  type        = number
  description = "RDS allocated storage in GiB."
  nullable    = false
}

variable "db_max_allocated_storage" {
  type        = number
  description = "RDS storage autoscaling ceiling in GiB."
  nullable    = false
}

variable "db_multi_az" {
  type        = bool
  description = "Enable RDS Multi-AZ. Development stays false."
  nullable    = false
}

variable "backup_retention_days" {
  type        = number
  description = "RDS backup retention in days."
  nullable    = false
}

variable "deletion_protection" {
  type        = bool
  description = "RDS and ALB deletion protection."
  nullable    = false
}

variable "performance_insights" {
  type        = bool
  description = "Enable RDS Performance Insights after a cost review."
  nullable    = false
  default     = false
}

variable "log_retention_days" {
  type        = number
  description = "CloudWatch log retention in days."
  nullable    = false
}

variable "secret_recovery_window_days" {
  type        = number
  description = "Secrets Manager recovery window."
  nullable    = false
}

variable "enable_web_versioning" {
  type        = bool
  description = "Version the static web bucket."
  nullable    = false
}

variable "enable_data_versioning" {
  type        = bool
  description = "Version the application data bucket."
  nullable    = false
}

variable "enable_access_logs" {
  type        = bool
  description = "Create an access-log bucket and attach it to S3, ALB, and CloudFront."
  nullable    = false
  default     = false
}

variable "enable_container_insights" {
  type        = bool
  description = "Enable ECS Container Insights after a cost review."
  nullable    = false
  default     = false
}

variable "domain_name" {
  type        = string
  description = "Optional custom domain. Empty uses the CloudFront domain."
  nullable    = false
  default     = ""
}

variable "hosted_zone_id" {
  type        = string
  description = "Route 53 hosted zone ID when create_dns_records is true."
  nullable    = false
  default     = ""
}

variable "create_dns_records" {
  type        = bool
  description = "Create Route 53 records for the certificate and distribution."
  nullable    = false
  default     = false
}

variable "additional_app_urls" {
  type        = list(string)
  description = "Extra HTTPS origins for Cognito callbacks, logout URLs, and CORS. Add the CloudFront URL after the first apply if no custom domain is set."
  nullable    = false
  default     = []
}

variable "mfa_configuration" {
  type        = string
  description = "Cognito MFA setting."
  nullable    = false
  default     = "OPTIONAL"
}

variable "allow_self_registration" {
  type        = bool
  description = "Allow public Cognito sign-up."
  nullable    = false
  default     = false
}

variable "bedrock_model_id" {
  type        = string
  description = "Bedrock model ID. Empty keeps AI_PROVIDER=stub and omits Bedrock IAM."
  nullable    = false
  default     = ""
}

variable "ai_provider" {
  type        = string
  description = "AI adapter. Keep stub until model access and live evaluation are complete."
  nullable    = false
  default     = "stub"
}

variable "alarm_email" {
  type        = string
  description = "Optional alarm email. The SNS subscription must be confirmed manually."
  nullable    = false
  default     = ""
}

variable "max_monthly_budget" {
  type        = number
  description = "Reserved for documentation of the environment cost target. Account budgets live in bootstrap."
  nullable    = false
  default     = 0
}

variable "price_class" {
  type        = string
  description = "CloudFront price class."
  nullable    = false
  default     = "PriceClass_100"
}

variable "original_file_retention_days" {
  type        = number
  description = "S3 lifecycle for uploads/."
  nullable    = false
  default     = 90
}

variable "error_report_retention_days" {
  type        = number
  description = "S3 lifecycle for errors/."
  nullable    = false
  default     = 30
}

variable "export_retention_days" {
  type        = number
  description = "S3 lifecycle for exports/."
  nullable    = false
  default     = 1
}
