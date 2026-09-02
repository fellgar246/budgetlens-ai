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
  description = "KMS key ARN used to encrypt images."
  nullable    = false
}

variable "image_count_limit" {
  type        = number
  description = "Maximum tagged images retained by the lifecycle policy."
  nullable    = false
  default     = 20

  validation {
    condition     = var.image_count_limit >= 5 && var.image_count_limit <= 100
    error_message = "image_count_limit must be between 5 and 100."
  }
}
