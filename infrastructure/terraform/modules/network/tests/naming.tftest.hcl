mock_provider "aws" {
  mock_data "aws_availability_zones" {
    defaults = {
      names = ["us-east-1a", "us-east-1b", "us-east-1c"]
    }
  }

  mock_data "aws_region" {
    defaults = {
      name   = "us-east-1"
      region = "us-east-1"
    }
  }

  mock_data "aws_caller_identity" {
    defaults = {
      account_id = "123456789012"
    }
  }

  mock_data "aws_iam_policy_document" {
    defaults = {
      json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":\"sts:AssumeRole\",\"Principal\":{\"Service\":\"vpc-flow-logs.amazonaws.com\"}}]}"
    }
  }
}

variables {
  name_prefix                = "budgetlens-dev"
  vpc_cidr                   = "10.40.0.0/16"
  availability_zone_count    = 2
  nat_gateway_count          = 1
  enable_vpc_flow_logs       = false
  enable_interface_endpoints = false
  flow_log_retention_days    = 14
  kms_key_arn                = "arn:aws:kms:us-east-1:123456789012:key/test"
}

run "names_follow_environment_convention" {
  command = plan

  assert {
    condition     = aws_vpc.this.tags["Name"] == "budgetlens-dev-vpc"
    error_message = "VPC name must be budgetlens-<environment>-vpc."
  }

  assert {
    condition     = aws_internet_gateway.this.tags["Name"] == "budgetlens-dev-igw"
    error_message = "Internet gateway name must follow budgetlens-<environment>-<resource>."
  }

  assert {
    condition     = length(aws_subnet.isolated) == 2
    error_message = "RDS isolation requires two isolated subnets."
  }
}

run "reject_invalid_name_prefix" {
  command = plan

  variables {
    name_prefix = "BudgetLens"
  }

  expect_failures = [
    var.name_prefix,
  ]
}

run "reject_nat_count_above_az_count" {
  command = plan

  variables {
    availability_zone_count = 2
    nat_gateway_count       = 3
  }

  expect_failures = [
    var.nat_gateway_count,
  ]
}
