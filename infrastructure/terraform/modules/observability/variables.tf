variable "name_prefix" {
  type        = string
  description = "Resource name prefix, for example budgetlens-dev."
  nullable    = false

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$", var.name_prefix))
    error_message = "name_prefix must be 3-32 lowercase alphanumeric characters or hyphens."
  }
}

variable "alarm_email" {
  type        = string
  description = "Optional email for alarm notifications. The subscription must be confirmed manually."
  nullable    = false
  default     = ""
}

variable "alb_arn_suffix" {
  type        = string
  description = "ALB ARN suffix used by CloudWatch metrics."
  nullable    = false
}

variable "cluster_name" {
  type        = string
  description = "ECS cluster name."
  nullable    = false
}

variable "service_name" {
  type        = string
  description = "ECS API service name."
  nullable    = false
}

variable "rds_identifier" {
  type        = string
  description = "RDS instance identifier."
  nullable    = false
}

variable "api_desired_count" {
  type        = number
  description = "Expected healthy API tasks."
  nullable    = false
}

variable "alarm_5xx_threshold" {
  type        = number
  description = "Sustained ALB 5xx count that raises an application alarm."
  nullable    = false
  default     = 5
}

variable "alarm_cpu_threshold" {
  type        = number
  description = "RDS CPU percent that raises a dependency alarm."
  nullable    = false
  default     = 80
}

variable "alarm_storage_threshold_bytes" {
  type        = number
  description = "RDS free-storage bytes that raise a dependency alarm."
  nullable    = false
  default     = 2147483648
}

variable "kms_key_arn" {
  type        = string
  description = "KMS key ARN used to encrypt the alarm topic."
  nullable    = false
}

variable "enable_container_insights" {
  type        = bool
  description = "Create the Container Insights running-task alarm only when that metric exists."
  nullable    = false
}

variable "acm_certificate_arn" {
  type        = string
  description = "Optional ACM certificate ARN to monitor for expiry."
  nullable    = false
  default     = ""
}
