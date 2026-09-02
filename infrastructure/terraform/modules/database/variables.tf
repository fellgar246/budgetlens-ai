variable "name_prefix" {
  type        = string
  description = "Resource name prefix, for example budgetlens-dev."
  nullable    = false

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$", var.name_prefix))
    error_message = "name_prefix must be 3-32 lowercase alphanumeric characters or hyphens."
  }
}

variable "vpc_id" {
  type        = string
  description = "VPC that hosts the isolated database subnets."
  nullable    = false
}

variable "isolated_subnet_ids" {
  type        = list(string)
  description = "Isolated subnet IDs with no internet route."
  nullable    = false

  validation {
    condition     = length(var.isolated_subnet_ids) >= 2
    error_message = "RDS requires at least two isolated subnets."
  }
}

variable "kms_key_arn" {
  type        = string
  description = "KMS key ARN for storage, secrets, and logs."
  nullable    = false
}

variable "instance_class" {
  type        = string
  description = "RDS instance class. Use a small class in development."
  nullable    = false
}

variable "allocated_storage" {
  type        = number
  description = "Initial storage in GiB."
  nullable    = false

  validation {
    condition     = var.allocated_storage >= 20 && var.allocated_storage <= 1000
    error_message = "allocated_storage must be between 20 and 1000 GiB."
  }
}

variable "max_allocated_storage" {
  type        = number
  description = "Storage autoscaling ceiling in GiB."
  nullable    = false

  validation {
    condition     = var.max_allocated_storage >= 20
    error_message = "max_allocated_storage must be at least 20 GiB."
  }
}

variable "multi_az" {
  type        = bool
  description = "Enable Multi-AZ. Required for production; development stays single-AZ."
  nullable    = false
}

variable "backup_retention_days" {
  type        = number
  description = "Automated backup retention in days."
  nullable    = false

  validation {
    condition     = var.backup_retention_days >= 1 && var.backup_retention_days <= 35
    error_message = "backup_retention_days must be between 1 and 35."
  }
}

variable "deletion_protection" {
  type        = bool
  description = "Prevent accidental deletion. Must be true in production."
  nullable    = false
}

variable "performance_insights" {
  type        = bool
  description = "Enable Performance Insights only after a cost and retention review."
  nullable    = false
}

variable "log_retention_days" {
  type        = number
  description = "CloudWatch retention for PostgreSQL logs."
  nullable    = false

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_days)
    error_message = "log_retention_days must be a CloudWatch Logs retention value."
  }
}

variable "secret_recovery_window_days" {
  type        = number
  description = "Secrets Manager recovery window. Use 0 only for disposable development."
  nullable    = false

  validation {
    condition     = var.secret_recovery_window_days == 0 || (var.secret_recovery_window_days >= 7 && var.secret_recovery_window_days <= 30)
    error_message = "secret_recovery_window_days must be 0 or between 7 and 30."
  }
}
