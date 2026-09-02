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
  cost_visible_sizes = {
    nat_gateway_count            = var.nat_gateway_count
    api_desired_count            = var.api_desired_count
    api_cpu                      = var.api_cpu
    api_memory                   = var.api_memory
    db_instance_class            = var.db_instance_class
    db_allocated_storage         = var.db_allocated_storage
    db_multi_az                  = var.db_multi_az
    log_retention_days           = var.log_retention_days
    enable_autoscaling           = var.enable_autoscaling
    autoscaling_max_count        = var.autoscaling_max_count
    backup_retention_days        = var.backup_retention_days
    price_class                  = var.price_class
    enable_waf                   = var.enable_waf
    enable_container_insights    = var.enable_container_insights
    enable_vpc_flow_logs         = var.enable_vpc_flow_logs
    enable_interface_endpoints   = var.enable_interface_endpoints
    enable_access_logs           = var.enable_access_logs
    ai_provider                  = var.ai_provider
    original_file_retention_days = var.original_file_retention_days
    error_report_retention_days  = var.error_report_retention_days
    export_retention_days        = var.export_retention_days
    deletion_protection          = var.deletion_protection
  }
}
