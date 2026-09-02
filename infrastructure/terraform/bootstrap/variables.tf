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
  description = "Optional email for the account budget and cost-anomaly subscription. Confirm the message manually. A budget is an alert, not a hard cap."
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

variable "budget_actual_percent_thresholds" {
  type        = list(number)
  description = "Actual-spend percentages that notify. Chosen alerts, not a spending cap."
  nullable    = false
  default     = [50, 80, 100]

  validation {
    condition     = alltrue([for value in var.budget_actual_percent_thresholds : value > 0 && value <= 200])
    error_message = "budget_actual_percent_thresholds must be percentages between 1 and 200."
  }
}

variable "budget_forecast_percent_thresholds" {
  type        = list(number)
  description = "Forecast-spend percentages that notify. Chosen alerts, not a spending cap."
  nullable    = false
  default     = [80, 100]

  validation {
    condition     = alltrue([for value in var.budget_forecast_percent_thresholds : value > 0 && value <= 200])
    error_message = "budget_forecast_percent_thresholds must be percentages between 1 and 200."
  }
}

variable "enable_cost_anomaly_detection" {
  type        = bool
  description = "Create Cost Anomaly Detection after Cost Explorer is enabled and the control is approved."
  nullable    = false
  default     = false
}

variable "cost_anomaly_impact_usd" {
  type        = number
  description = "Absolute USD impact that raises a cost-anomaly alert. Not a monthly cost figure."
  nullable    = false
  default     = 20

  validation {
    condition     = var.cost_anomaly_impact_usd >= 0
    error_message = "cost_anomaly_impact_usd must be zero or positive."
  }
}

variable "enable_cost_allocation_tags" {
  type        = bool
  description = "Activate Cost Explorer allocation tags after Cost Explorer is enabled."
  nullable    = false
  default     = false
}
