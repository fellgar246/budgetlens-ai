data "aws_caller_identity" "current" {}

resource "random_id" "suffix" {
  byte_length = 4
}

locals {
  state_bucket         = "budgetlens-tfstate-${data.aws_caller_identity.current.account_id}-${random_id.suffix.hex}"
  create_oidc          = var.github_owner != "" && var.github_repository != ""
  create_budget        = var.max_monthly_budget > 0 && var.alarm_email != ""
  create_cost_anomaly  = var.enable_cost_anomaly_detection && var.alarm_email != ""
  cost_allocation_tags = var.enable_cost_allocation_tags ? toset(["Project", "Environment", "CostCenter", "Owner"]) : toset([])
}

data "aws_iam_policy_document" "state_kms" {
  # checkov:skip=CKV_AWS_109: Account-root key policy is the AWS default administration pattern.
  # checkov:skip=CKV_AWS_111: Account-root key policy is the AWS default administration pattern.
  # checkov:skip=CKV_AWS_356: KMS key policies use Resource=* on the key itself.
  statement {
    sid     = "EnableRootAccount"
    effect  = "Allow"
    actions = ["kms:*"]
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
    resources = ["*"]
  }
}

resource "aws_kms_key" "state" {
  description             = "Terraform state encryption for BudgetLens"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  policy                  = data.aws_iam_policy_document.state_kms.json
}

resource "aws_kms_alias" "state" {
  name          = "alias/budgetlens-tfstate"
  target_key_id = aws_kms_key.state.key_id
}

resource "aws_s3_bucket" "state" {
  # checkov:skip=CKV_AWS_18: Access logs would require a second bucket; versioning and TLS are the recovery controls.
  # checkov:skip=CKV_AWS_144: State stays in one region; versioning is the recovery control.
  # checkov:skip=CKV2_AWS_62: State change notifications are not required.
  bucket        = local.state_bucket
  force_destroy = false
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.state.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    id     = "expire-noncurrent-state"
    status = "Enabled"

    filter {
      prefix = ""
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

data "aws_iam_policy_document" "state" {
  statement {
    sid     = "DenyInsecureTransport"
    effect  = "Deny"
    actions = ["s3:*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    resources = [
      aws_s3_bucket.state.arn,
      "${aws_s3_bucket.state.arn}/*",
    ]
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }

  statement {
    sid     = "DenyPublicAcls"
    effect  = "Deny"
    actions = ["s3:PutBucketPublicAccessBlock"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    resources = [aws_s3_bucket.state.arn]
    condition {
      test     = "StringNotEquals"
      variable = "aws:PrincipalAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_s3_bucket_policy" "state" {
  bucket = aws_s3_bucket.state.id
  policy = data.aws_iam_policy_document.state.json
}

module "github_oidc" {
  count  = local.create_oidc ? 1 : 0
  source = "../modules/github_oidc"

  name_prefix           = "budgetlens"
  github_owner          = var.github_owner
  github_repository     = var.github_repository
  state_bucket_arn      = aws_s3_bucket.state.arn
  create_provider       = var.create_oidc_provider
  existing_provider_arn = var.existing_oidc_provider_arn
}

resource "aws_budgets_budget" "monthly" {
  count = local.create_budget ? 1 : 0

  name         = "budgetlens-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.max_monthly_budget)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  dynamic "notification" {
    for_each = var.budget_actual_percent_thresholds
    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = notification.value
      threshold_type             = "PERCENTAGE"
      notification_type          = "ACTUAL"
      subscriber_email_addresses = [var.alarm_email]
    }
  }

  dynamic "notification" {
    for_each = var.budget_forecast_percent_thresholds
    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = notification.value
      threshold_type             = "PERCENTAGE"
      notification_type          = "FORECASTED"
      subscriber_email_addresses = [var.alarm_email]
    }
  }
}

resource "aws_ce_anomaly_monitor" "services" {
  count = local.create_cost_anomaly ? 1 : 0

  name              = "budgetlens-service-monitor"
  monitor_type      = "DIMENSIONAL"
  monitor_dimension = "SERVICE"
}

resource "aws_ce_anomaly_subscription" "email" {
  count = local.create_cost_anomaly ? 1 : 0

  name      = "budgetlens-anomaly-alerts"
  frequency = "DAILY"

  monitor_arn_list = [
    aws_ce_anomaly_monitor.services[0].arn,
  ]

  subscriber {
    type    = "EMAIL"
    address = var.alarm_email
  }

  threshold_expression {
    dimension {
      key           = "ANOMALY_TOTAL_IMPACT_ABSOLUTE"
      match_options = ["GREATER_THAN_OR_EQUAL"]
      values        = [tostring(var.cost_anomaly_impact_usd)]
    }
  }
}

resource "aws_ce_cost_allocation_tag" "required" {
  for_each = local.cost_allocation_tags

  tag_key = each.key
  status  = "Active"
}
