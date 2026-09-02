resource "random_password" "master" {
  length           = 32
  special          = false
  override_special = ""
}

resource "random_password" "pepper" {
  length  = 48
  special = false
}

resource "aws_security_group" "rds" {
  name        = "${var.name_prefix}-rds"
  description = "PostgreSQL access for ${var.name_prefix} ECS tasks only"
  vpc_id      = var.vpc_id

  tags = {
    Name = "${var.name_prefix}-rds"
  }
}

resource "aws_vpc_security_group_egress_rule" "rds_https_monitoring" {
  security_group_id = aws_security_group.rds.id
  description       = "HTTPS for RDS monitoring endpoints"
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
}

resource "aws_db_subnet_group" "this" {
  name       = "${var.name_prefix}-db"
  subnet_ids = var.isolated_subnet_ids

  tags = {
    Name = "${var.name_prefix}-db"
  }
}

resource "aws_db_parameter_group" "this" {
  name        = "${var.name_prefix}-postgres16"
  family      = "postgres16"
  description = "BudgetLens PostgreSQL 16 parameters for ${var.name_prefix}"

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_disconnections"
    value = "1"
  }

  parameter {
    name         = "rds.force_ssl"
    value        = "1"
    apply_method = "pending-reboot"
  }
}

resource "aws_cloudwatch_log_group" "postgresql" {
  # checkov:skip=CKV_AWS_338: Retention follows the environment log policy.
  name              = "/aws/rds/instance/${var.name_prefix}/postgresql"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.kms_key_arn
}

resource "aws_cloudwatch_log_group" "upgrade" {
  # checkov:skip=CKV_AWS_338: Retention follows the environment log policy.
  name              = "/aws/rds/instance/${var.name_prefix}/upgrade"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.kms_key_arn
}

resource "aws_db_instance" "this" {
  # checkov:skip=CKV_AWS_157: Multi-AZ is environment-driven; production enables it.
  # checkov:skip=CKV_AWS_293: Deletion protection is environment-driven; production enables it.
  # checkov:skip=CKV_AWS_353: Performance Insights stay off until a cost review.
  identifier                            = var.name_prefix
  engine                                = "postgres"
  engine_version                        = "16"
  instance_class                        = var.instance_class
  allocated_storage                     = var.allocated_storage
  max_allocated_storage                 = max(var.max_allocated_storage, var.allocated_storage)
  storage_type                          = "gp3"
  storage_encrypted                     = true
  kms_key_id                            = var.kms_key_arn
  db_name                               = "budgetlens"
  username                              = "budgetlens"
  password                              = random_password.master.result
  port                                  = 5432
  db_subnet_group_name                  = aws_db_subnet_group.this.name
  parameter_group_name                  = aws_db_parameter_group.this.name
  vpc_security_group_ids                = [aws_security_group.rds.id]
  publicly_accessible                   = false
  multi_az                              = var.multi_az
  deletion_protection                   = var.deletion_protection
  backup_retention_period               = var.backup_retention_days
  backup_window                         = "07:00-08:00"
  maintenance_window                    = "sun:08:00-sun:09:00"
  auto_minor_version_upgrade            = true
  copy_tags_to_snapshot                 = true
  delete_automated_backups              = false
  skip_final_snapshot                   = !var.deletion_protection
  final_snapshot_identifier             = var.deletion_protection ? "${var.name_prefix}-final" : null
  iam_database_authentication_enabled   = true
  performance_insights_enabled          = var.performance_insights
  performance_insights_kms_key_id       = var.performance_insights ? var.kms_key_arn : null
  performance_insights_retention_period = var.performance_insights ? 7 : null
  enabled_cloudwatch_logs_exports       = ["postgresql", "upgrade"]
  monitoring_interval                   = 60
  monitoring_role_arn                   = aws_iam_role.monitoring.arn
  apply_immediately                     = false

  # prevent_destroy cannot take a variable. Production uses deletion_protection
  # so the documented teardown runbook can disable protection and destroy after review.
  lifecycle {
    prevent_destroy = false
  }
}

resource "aws_iam_role" "monitoring" {
  name = "${var.name_prefix}-rds-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "monitoring" {
  role       = aws_iam_role.monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

resource "aws_secretsmanager_secret" "app" {
  # checkov:skip=CKV2_AWS_57: Rotation is an operator process; the secret is generated, never committed.
  name                    = "${var.name_prefix}/app"
  description             = "Runtime secrets for ${var.name_prefix}. Values are never Terraform outputs."
  kms_key_id              = var.kms_key_arn
  recovery_window_in_days = var.secret_recovery_window_days
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    DATABASE_URL       = "postgresql+psycopg://budgetlens:${random_password.master.result}@${aws_db_instance.this.address}:5432/budgetlens"
    STORAGE_KEY_PEPPER = random_password.pepper.result
  })
}
