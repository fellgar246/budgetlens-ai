variable "name_prefix" {
  type        = string
  description = "Resource name prefix, for example budgetlens-dev."
  nullable    = false

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$", var.name_prefix))
    error_message = "name_prefix must be 3-32 lowercase alphanumeric characters or hyphens."
  }
}

variable "web_bucket_id" {
  type        = string
  description = "Private static-web bucket name."
  nullable    = false
}

variable "web_bucket_arn" {
  type        = string
  description = "Private static-web bucket ARN."
  nullable    = false
}

variable "web_bucket_regional_domain_name" {
  type        = string
  description = "Regional domain name of the static-web bucket."
  nullable    = false
}

variable "alb_dns_name" {
  type        = string
  description = "ALB DNS name used as the /api/* origin."
  nullable    = false
}

variable "domain_name" {
  type        = string
  description = "Optional custom domain. Empty uses the CloudFront domain."
  nullable    = false
  default     = ""
}

variable "hosted_zone_id" {
  type        = string
  description = "Route 53 hosted zone ID. Required only when create_dns_records is true."
  nullable    = false
  default     = ""
}

variable "create_dns_records" {
  type        = bool
  description = "Create Route 53 records for the certificate and the distribution."
  nullable    = false
}

variable "waf_web_acl_arn" {
  type        = string
  description = "Optional CloudFront WAF web ACL ARN."
  nullable    = false
  default     = ""
}

variable "price_class" {
  type        = string
  description = "CloudFront price class. PriceClass_100 is enough for a development demo."
  nullable    = false
  default     = "PriceClass_100"

  validation {
    condition     = contains(["PriceClass_100", "PriceClass_200", "PriceClass_All"], var.price_class)
    error_message = "price_class must be a CloudFront price class."
  }
}
