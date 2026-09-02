variable "name_prefix" {
  type        = string
  description = "Resource name prefix, for example budgetlens."
  nullable    = false

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$", var.name_prefix))
    error_message = "name_prefix must be 3-32 lowercase alphanumeric characters or hyphens."
  }
}

variable "github_owner" {
  type        = string
  description = "GitHub organization or user that owns the repository."
  nullable    = false
}

variable "github_repository" {
  type        = string
  description = "GitHub repository name without the owner prefix."
  nullable    = false
}

variable "state_bucket_arn" {
  type        = string
  description = "Terraform state bucket ARN the roles may read and lock."
  nullable    = false
}

variable "create_provider" {
  type        = bool
  description = "Create the GitHub OIDC provider. Set false when the account already has one."
  nullable    = false
  default     = true
}

variable "existing_provider_arn" {
  type        = string
  description = "Existing GitHub OIDC provider ARN when create_provider is false."
  nullable    = false
  default     = ""
}
