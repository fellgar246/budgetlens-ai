variable "name_prefix" {
  type        = string
  description = "Resource name prefix, for example budgetlens-dev."
  nullable    = false

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$", var.name_prefix))
    error_message = "name_prefix must be 3-32 lowercase alphanumeric characters or hyphens."
  }
}

variable "vpc_cidr" {
  type        = string
  description = "IPv4 CIDR for the environment VPC."
  nullable    = false

  validation {
    condition     = can(cidrnetmask(var.vpc_cidr))
    error_message = "vpc_cidr must be a valid IPv4 CIDR."
  }
}

variable "availability_zone_count" {
  type        = number
  description = "Number of Availability Zones. Must be at least 2."
  nullable    = false

  validation {
    condition     = var.availability_zone_count >= 2 && var.availability_zone_count <= 3
    error_message = "availability_zone_count must be 2 or 3."
  }
}

variable "nat_gateway_count" {
  type        = number
  description = "NAT Gateways to create. 1 reduces cost; match AZ count for production resilience."
  nullable    = false

  validation {
    condition     = var.nat_gateway_count >= 1 && var.nat_gateway_count <= 3
    error_message = "nat_gateway_count must be between 1 and 3."
  }
}

variable "enable_vpc_flow_logs" {
  type        = bool
  description = "Send VPC flow logs to CloudWatch. Disable only after a cost review."
  nullable    = false
}

variable "enable_interface_endpoints" {
  type        = bool
  description = "Create interface VPC endpoints for ECR, logs, Secrets Manager, STS, and Bedrock Runtime."
  nullable    = false
}

variable "flow_log_retention_days" {
  type        = number
  description = "CloudWatch retention for VPC flow logs."
  nullable    = false

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.flow_log_retention_days)
    error_message = "flow_log_retention_days must be a CloudWatch Logs retention value."
  }
}

variable "kms_key_arn" {
  type        = string
  description = "KMS key ARN used to encrypt flow-log groups."
  nullable    = false
}
