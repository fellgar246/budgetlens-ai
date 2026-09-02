locals {
  name_prefix = "${var.project_name}-${var.environment}"
  required_tags = {
    Project            = "BudgetLens"
    Environment        = var.environment
    ManagedBy          = "Terraform"
    Owner              = var.owner
    CostCenter         = var.cost_center
    DataClassification = var.data_classification
  }
  configured_app_urls = compact(concat(
    var.domain_name == "" ? [] : ["https://${var.domain_name}"],
    var.additional_app_urls,
  ))
  app_urls      = length(local.configured_app_urls) > 0 ? local.configured_app_urls : ["https://localhost"]
  callback_urls = [for url in local.app_urls : "${trimsuffix(url, "/")}/login"]
  logout_urls   = [for url in local.app_urls : "${trimsuffix(url, "/")}/"]
  cors_origins  = join(",", local.app_urls)
}
