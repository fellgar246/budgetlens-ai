variable "aws_region" {
  type        = string
  description = "AWS region for the state bucket and OIDC roles."
  nullable    = false
  default     = "us-east-1"
}

variable "aws_account_id" {
  type        = string
  description = "Twelve-digit AWS account ID. Empty disables allowed_account_ids until a human records the account."
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

variable "github_owner" {
  type        = string
  description = "GitHub owner. Leave empty to skip OIDC roles."
  nullable    = false
  default     = ""
}

variable "github_repository" {
  type        = string
  description = "GitHub repository name. Leave empty to skip OIDC roles."
  nullable    = false
  default     = ""
}

variable "create_oidc_provider" {
  type        = bool
  description = "Create the GitHub OIDC provider. Set false when the account already has one."
  nullable    = false
  default     = true
}

variable "existing_oidc_provider_arn" {
  type        = string
  description = "Existing GitHub OIDC provider ARN when create_oidc_provider is false."
  nullable    = false
  default     = ""
}

variable "alarm_email" {
  type        = string
  description = "Optional email for the account budget. The subscription must be confirmed manually."
  nullable    = false
  default     = ""
}

variable "max_monthly_budget" {
  type        = number
  description = "Monthly AWS budget in USD. 0 skips budget creation. A budget is an alert, not a hard cap."
  nullable    = false
  default     = 0

  validation {
    condition     = var.max_monthly_budget >= 0
    error_message = "max_monthly_budget must be zero or positive."
  }
}
