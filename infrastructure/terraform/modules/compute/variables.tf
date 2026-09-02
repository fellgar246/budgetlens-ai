variable "name_prefix" {
  type        = string
  description = "Resource name prefix, for example budgetlens-dev."
  nullable    = false

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$", var.name_prefix))
    error_message = "name_prefix must be 3-32 lowercase alphanumeric characters or hyphens."
  }
}

variable "environment" {
  type        = string
  description = "Environment name: dev or prod."
  nullable    = false

  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "environment must be dev or prod."
  }
}

variable "vpc_id" {
  type        = string
  description = "VPC identifier."
  nullable    = false
}

variable "public_subnet_ids" {
  type        = list(string)
  description = "Public subnets for the load balancer."
  nullable    = false
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnets for ECS tasks."
  nullable    = false
}

variable "kms_key_arn" {
  type        = string
  description = "KMS key ARN for logs and secret decryption."
  nullable    = false
}

variable "ecr_repository_arn" {
  type        = string
  description = "API ECR repository ARN."
  nullable    = false
}

variable "data_bucket_arn" {
  type        = string
  description = "Application data bucket ARN."
  nullable    = false
}

variable "app_secret_arn" {
  type        = string
  description = "Secrets Manager ARN that stores DATABASE_URL and STORAGE_KEY_PEPPER."
  nullable    = false
}

variable "rds_security_group_id" {
  type        = string
  description = "RDS security group that receives ingress from the ECS tasks."
  nullable    = false
}

variable "api_image" {
  type        = string
  description = "API image URI with an immutable tag or digest. The latest tag is rejected."
  nullable    = false

  validation {
    condition     = !can(regex(":(latest|LATEST)$", var.api_image)) && trimspace(var.api_image) != ""
    error_message = "api_image must not use the latest tag. Prefer a digest."
  }
}

variable "api_cpu" {
  type        = number
  description = "Fargate CPU units for the API task."
  nullable    = false

  validation {
    condition     = contains([256, 512, 1024, 2048], var.api_cpu)
    error_message = "api_cpu must be a valid Fargate CPU value."
  }
}

variable "api_memory" {
  type        = number
  description = "Fargate memory in MiB for the API task."
  nullable    = false

  validation {
    condition     = var.api_memory >= 512 && var.api_memory <= 8192
    error_message = "api_memory must be between 512 and 8192."
  }
}

variable "api_desired_count" {
  type        = number
  description = "Desired API tasks. Development uses 1; production uses 2 or more."
  nullable    = false

  validation {
    condition     = var.api_desired_count >= 1 && var.api_desired_count <= 8
    error_message = "api_desired_count must be between 1 and 8."
  }
}

variable "enable_autoscaling" {
  type        = bool
  description = "Enable ECS service autoscaling."
  nullable    = false
}

variable "autoscaling_max_count" {
  type        = number
  description = "Maximum API tasks when autoscaling is enabled."
  nullable    = false
  default     = 4
}

variable "log_retention_days" {
  type        = number
  description = "CloudWatch log retention for API and migration tasks."
  nullable    = false

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_days)
    error_message = "log_retention_days must be a CloudWatch Logs retention value."
  }
}

variable "enable_container_insights" {
  type        = bool
  description = "Enable Container Insights only after a cost review."
  nullable    = false
}

variable "enable_alb_access_logs" {
  type        = bool
  description = "Write ALB access logs to the dedicated logs bucket."
  nullable    = false
}

variable "logs_bucket_id" {
  type        = string
  description = "Access-log bucket name. Required when enable_alb_access_logs is true."
  nullable    = false
  default     = ""
}

variable "alb_deletion_protection" {
  type        = bool
  description = "Protect the load balancer from deletion."
  nullable    = false
}

variable "bedrock_region" {
  type        = string
  description = "Region used for Bedrock Runtime calls."
  nullable    = false
}

variable "bedrock_model_id" {
  type        = string
  description = "Bedrock model ID. Empty keeps the task role free of Bedrock actions."
  nullable    = false
  default     = ""
}

variable "ai_provider" {
  type        = string
  description = "AI adapter: stub or bedrock."
  nullable    = false

  validation {
    condition     = contains(["stub", "bedrock"], var.ai_provider)
    error_message = "ai_provider must be stub or bedrock."
  }
}

variable "cors_origins" {
  type        = string
  description = "Comma-separated browser origins allowed by the API."
  nullable    = false
}

variable "oidc_issuer" {
  type        = string
  description = "OIDC issuer URL."
  nullable    = false
}

variable "oidc_audience" {
  type        = string
  description = "OIDC audience (Cognito app client ID)."
  nullable    = false
}

variable "oidc_jwks_url" {
  type        = string
  description = "OIDC JWKS URL."
  nullable    = false
}

variable "data_bucket_id" {
  type        = string
  description = "Application data bucket name."
  nullable    = false
}

variable "aws_region" {
  type        = string
  description = "AWS region for the API process."
  nullable    = false
}

variable "create_seed_task" {
  type        = bool
  description = "Create an explicit seed task definition. Never attached to a service."
  nullable    = false
}

variable "git_sha" {
  type        = string
  description = "Git commit SHA recorded on the task definition and /version."
  nullable    = false
  default     = "unknown"
}

variable "app_version" {
  type        = string
  description = "Application SemVer recorded on the task definition and /version."
  nullable    = false
  default     = "0.1.0"
}
