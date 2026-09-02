variable "name_prefix" {
  type        = string
  description = "Resource name prefix, for example budgetlens-dev."
  nullable    = false

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$", var.name_prefix))
    error_message = "name_prefix must be 3-32 lowercase alphanumeric characters or hyphens."
  }
}

variable "callback_urls" {
  type        = list(string)
  description = "Allowed OAuth callback URLs for the public web client."
  nullable    = false

  validation {
    condition     = length(var.callback_urls) > 0 && alltrue([for url in var.callback_urls : can(regex("^https://", url))])
    error_message = "callback_urls must be a non-empty list of https URLs."
  }
}

variable "logout_urls" {
  type        = list(string)
  description = "Allowed OAuth logout URLs for the public web client."
  nullable    = false

  validation {
    condition     = length(var.logout_urls) > 0 && alltrue([for url in var.logout_urls : can(regex("^https://", url))])
    error_message = "logout_urls must be a non-empty list of https URLs."
  }
}

variable "mfa_configuration" {
  type        = string
  description = "Cognito MFA setting: OFF, OPTIONAL, or ON. Production should not stay OFF without a policy decision."
  nullable    = false

  validation {
    condition     = contains(["OFF", "OPTIONAL", "ON"], var.mfa_configuration)
    error_message = "mfa_configuration must be OFF, OPTIONAL, or ON."
  }
}

variable "deletion_protection" {
  type        = bool
  description = "Protect the user pool from deletion."
  nullable    = false
  default     = true
}

variable "allow_self_registration" {
  type        = bool
  description = "Allow public Cognito sign-up. Keep false until a user-policy review."
  nullable    = false
}

variable "access_token_minutes" {
  type        = number
  description = "Access token lifetime in minutes."
  nullable    = false
  default     = 60

  validation {
    condition     = var.access_token_minutes >= 5 && var.access_token_minutes <= 1440
    error_message = "access_token_minutes must be between 5 and 1440."
  }
}

variable "refresh_token_hours" {
  type        = number
  description = "Refresh token lifetime in hours."
  nullable    = false
  default     = 24

  validation {
    condition     = var.refresh_token_hours >= 1 && var.refresh_token_hours <= 720
    error_message = "refresh_token_hours must be between 1 and 720."
  }
}
