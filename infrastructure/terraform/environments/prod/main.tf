module "security" {
  source = "../../modules/security"

  providers = {
    aws           = aws
    aws.us_east_1 = aws.us_east_1
  }

  name_prefix = local.name_prefix
  enable_waf  = var.enable_waf
}

module "network" {
  source = "../../modules/network"

  name_prefix                = local.name_prefix
  vpc_cidr                   = var.vpc_cidr
  availability_zone_count    = var.availability_zone_count
  nat_gateway_count          = var.nat_gateway_count
  enable_vpc_flow_logs       = var.enable_vpc_flow_logs
  enable_interface_endpoints = var.enable_interface_endpoints
  flow_log_retention_days    = var.log_retention_days
  kms_key_arn                = module.security.kms_key_arn
}

module "ecr" {
  source = "../../modules/ecr"

  name_prefix = local.name_prefix
  kms_key_arn = module.security.kms_key_arn
}

module "storage" {
  source = "../../modules/storage"

  name_prefix                  = local.name_prefix
  kms_key_arn                  = module.security.kms_key_arn
  enable_web_versioning        = var.enable_web_versioning
  enable_data_versioning       = var.enable_data_versioning
  enable_access_logs           = var.enable_access_logs
  cors_allowed_origins         = local.configured_app_urls
  original_file_retention_days = var.original_file_retention_days
  error_report_retention_days  = var.error_report_retention_days
  export_retention_days        = var.export_retention_days
}

module "identity" {
  source = "../../modules/identity"

  name_prefix             = local.name_prefix
  callback_urls           = local.callback_urls
  logout_urls             = local.logout_urls
  mfa_configuration       = var.mfa_configuration
  allow_self_registration = var.allow_self_registration
  deletion_protection     = var.deletion_protection
}

module "database" {
  source = "../../modules/database"

  name_prefix                 = local.name_prefix
  vpc_id                      = module.network.vpc_id
  isolated_subnet_ids         = module.network.isolated_subnet_ids
  kms_key_arn                 = module.security.kms_key_arn
  instance_class              = var.db_instance_class
  allocated_storage           = var.db_allocated_storage
  max_allocated_storage       = var.db_max_allocated_storage
  multi_az                    = var.db_multi_az
  backup_retention_days       = var.backup_retention_days
  deletion_protection         = var.deletion_protection
  performance_insights        = var.performance_insights
  log_retention_days          = var.log_retention_days
  secret_recovery_window_days = var.secret_recovery_window_days
}

module "compute" {
  source = "../../modules/compute"

  name_prefix               = local.name_prefix
  environment               = var.environment
  vpc_id                    = module.network.vpc_id
  public_subnet_ids         = module.network.public_subnet_ids
  private_subnet_ids        = module.network.private_subnet_ids
  kms_key_arn               = module.security.kms_key_arn
  ecr_repository_arn        = module.ecr.repository_arn
  data_bucket_arn           = module.storage.data_bucket_arn
  data_bucket_id            = module.storage.data_bucket_id
  app_secret_arn            = module.database.app_secret_arn
  rds_security_group_id     = module.database.security_group_id
  api_image                 = var.api_image
  api_cpu                   = var.api_cpu
  api_memory                = var.api_memory
  api_desired_count         = var.api_desired_count
  enable_autoscaling        = var.enable_autoscaling
  autoscaling_max_count     = var.autoscaling_max_count
  log_retention_days        = var.log_retention_days
  enable_container_insights = var.enable_container_insights
  enable_alb_access_logs    = var.enable_access_logs
  logs_bucket_id            = module.storage.logs_bucket_id
  alb_deletion_protection   = var.deletion_protection
  bedrock_region            = var.aws_region
  bedrock_model_id          = var.bedrock_model_id
  ai_provider               = var.ai_provider
  cors_origins              = local.cors_origins
  oidc_issuer               = module.identity.issuer
  oidc_audience             = module.identity.client_id
  oidc_jwks_url             = module.identity.jwks_url
  aws_region                = var.aws_region
  create_seed_task          = false
}

module "edge" {
  source = "../../modules/edge"

  providers = {
    aws           = aws
    aws.us_east_1 = aws.us_east_1
  }

  name_prefix                     = local.name_prefix
  web_bucket_id                   = module.storage.web_bucket_id
  web_bucket_arn                  = module.storage.web_bucket_arn
  web_bucket_regional_domain_name = module.storage.web_bucket_regional_domain_name
  alb_dns_name                    = module.compute.alb_dns_name
  domain_name                     = var.domain_name
  hosted_zone_id                  = var.hosted_zone_id
  create_dns_records              = var.create_dns_records
  waf_web_acl_arn                 = module.security.waf_web_acl_arn
  price_class                     = var.price_class
}

module "observability" {
  source = "../../modules/observability"

  name_prefix               = local.name_prefix
  kms_key_arn               = module.security.kms_key_arn
  alarm_email               = var.alarm_email
  alb_arn_suffix            = module.compute.alb_arn_suffix
  cluster_name              = module.compute.cluster_name
  service_name              = module.compute.service_name
  rds_identifier            = module.database.identifier
  api_desired_count         = var.api_desired_count
  enable_container_insights = var.enable_container_insights
  acm_certificate_arn       = coalesce(module.edge.acm_certificate_arn, "")
}
