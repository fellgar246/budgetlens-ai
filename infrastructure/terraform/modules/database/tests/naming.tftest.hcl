mock_provider "aws" {}

variables {
  name_prefix                 = "budgetlens-dev"
  vpc_id                      = "vpc-0123456789abcdef0"
  isolated_subnet_ids         = ["subnet-isolated-a", "subnet-isolated-b"]
  kms_key_arn                 = "arn:aws:kms:us-east-1:123456789012:key/test"
  instance_class              = "db.t4g.micro"
  allocated_storage           = 20
  max_allocated_storage       = 40
  multi_az                    = false
  backup_retention_days       = 7
  deletion_protection         = false
  performance_insights        = false
  log_retention_days          = 14
  secret_recovery_window_days = 0
}

run "keeps_rds_private_and_named" {
  command = plan

  assert {
    condition     = aws_db_instance.this.identifier == "budgetlens-dev"
    error_message = "RDS identifier must be the environment name prefix."
  }

  assert {
    condition     = aws_db_instance.this.publicly_accessible == false
    error_message = "RDS must not be publicly accessible."
  }

  assert {
    condition     = aws_security_group.rds.name == "budgetlens-dev-rds"
    error_message = "RDS security group must follow budgetlens-<environment>-rds."
  }
}

run "reject_single_isolated_subnet" {
  command = plan

  variables {
    isolated_subnet_ids = ["subnet-isolated-a"]
  }

  expect_failures = [
    var.isolated_subnet_ids,
  ]
}
