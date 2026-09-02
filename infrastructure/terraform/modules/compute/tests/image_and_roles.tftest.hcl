mock_provider "aws" {
  mock_data "aws_region" {
    defaults = {
      name   = "us-east-1"
      region = "us-east-1"
    }
  }

  mock_data "aws_partition" {
    defaults = {
      partition = "aws"
    }
  }

  mock_data "aws_ec2_managed_prefix_list" {
    defaults = {
      id = "pl-mock-cloudfront"
    }
  }

  mock_data "aws_iam_policy_document" {
    defaults = {
      json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":\"sts:AssumeRole\",\"Principal\":{\"Service\":\"ecs-tasks.amazonaws.com\"}}]}"
    }
  }
}

variables {
  name_prefix               = "budgetlens-dev"
  environment               = "dev"
  vpc_id                    = "vpc-0123456789abcdef0"
  public_subnet_ids         = ["subnet-public-a", "subnet-public-b"]
  private_subnet_ids        = ["subnet-private-a", "subnet-private-b"]
  kms_key_arn               = "arn:aws:kms:us-east-1:123456789012:key/test"
  ecr_repository_arn        = "arn:aws:ecr:us-east-1:123456789012:repository/budgetlens-dev-api"
  data_bucket_arn           = "arn:aws:s3:::budgetlens-dev-data-test"
  data_bucket_id            = "budgetlens-dev-data-test"
  app_secret_arn            = "arn:aws:secretsmanager:us-east-1:123456789012:secret:budgetlens-dev/app"
  rds_security_group_id     = "sg-0123456789abcdef0"
  api_image                 = "123456789012.dkr.ecr.us-east-1.amazonaws.com/budgetlens-dev-api@sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  api_cpu                   = 256
  api_memory                = 512
  api_desired_count         = 1
  enable_autoscaling        = false
  log_retention_days        = 14
  enable_container_insights = false
  enable_alb_access_logs    = false
  alb_deletion_protection   = false
  bedrock_region            = "us-east-1"
  ai_provider               = "stub"
  cors_origins              = "https://localhost"
  oidc_issuer               = "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_example"
  oidc_audience             = "example-client"
  oidc_jwks_url             = "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_example/.well-known/jwks.json"
  aws_region                = "us-east-1"
  create_seed_task          = true
}

run "reject_latest_image_tag" {
  command = plan

  variables {
    api_image = "123456789012.dkr.ecr.us-east-1.amazonaws.com/budgetlens-dev-api:latest"
  }

  expect_failures = [
    var.api_image,
  ]
}

run "separates_execution_runtime_and_migration_roles" {
  command = plan

  assert {
    condition     = aws_iam_role.execution.name == "budgetlens-dev-execution"
    error_message = "Task execution role must be named budgetlens-<environment>-execution."
  }

  assert {
    condition     = aws_iam_role.task.name == "budgetlens-dev-task"
    error_message = "Task runtime role must be named budgetlens-<environment>-task."
  }

  assert {
    condition     = aws_iam_role.migration.name == "budgetlens-dev-migration"
    error_message = "Migration role must be named budgetlens-<environment>-migration."
  }

  assert {
    condition     = aws_ecs_task_definition.api.family == "budgetlens-dev-api"
    error_message = "API task family must follow budgetlens-<environment>-api."
  }
}
