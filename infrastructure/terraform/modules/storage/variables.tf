variable "name_prefix" {
  type        = string
  description = "Resource name prefix, for example budgetlens-dev."
  nullable    = false

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$", var.name_prefix))
    error_message = "name_prefix must be 3-32 lowercase alphanumeric characters or hyphens."
  }
}

variable "kms_key_arn" {
  type        = string
  description = "KMS key ARN used for default bucket encryption."
  nullable    = false
}

variable "enable_web_versioning" {
  type        = bool
  description = "Version the static web bucket. Recommended when asset rollback is needed."
  nullable    = false
}

variable "enable_data_versioning" {
  type        = bool
  description = "Version the application data bucket."
  nullable    = false
}

variable "enable_access_logs" {
  type        = bool
  description = "Create a dedicated access-log bucket and attach it to the web and data buckets."
  nullable    = false
}

variable "cors_allowed_origins" {
  type        = list(string)
  description = "Origins allowed for browser uploads to the data bucket. Empty disables CORS."
  nullable    = false
  default     = []
}

variable "original_file_retention_days" {
  type        = number
  description = "Expire objects under uploads/ after this many days."
  nullable    = false

  validation {
    condition     = var.original_file_retention_days >= 1 && var.original_file_retention_days <= 365
    error_message = "original_file_retention_days must be between 1 and 365."
  }
}

variable "error_report_retention_days" {
  type        = number
  description = "Expire objects under errors/ after this many days."
  nullable    = false

  validation {
    condition     = var.error_report_retention_days >= 1 && var.error_report_retention_days <= 365
    error_message = "error_report_retention_days must be between 1 and 365."
  }
}

variable "export_retention_days" {
  type        = number
  description = "Expire objects under exports/ after this many days."
  nullable    = false

  validation {
    condition     = var.export_retention_days >= 1 && var.export_retention_days <= 30
    error_message = "export_retention_days must be between 1 and 30."
  }
}
