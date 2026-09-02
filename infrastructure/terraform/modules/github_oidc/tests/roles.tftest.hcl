mock_provider "aws" {
  mock_data "aws_iam_policy_document" {
    defaults = {
      json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":\"sts:AssumeRoleWithWebIdentity\",\"Principal\":{\"Federated\":\"arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com\"}}]}"
    }
  }
}

variables {
  name_prefix       = "budgetlens"
  github_owner      = "example"
  github_repository = "budgetlens"
  state_bucket_arn  = "arn:aws:s3:::budgetlens-tfstate-example"
}

run "separates_plan_and_environment_deploy_roles" {
  command = plan

  assert {
    condition     = aws_iam_role.plan.name == "budgetlens-github-plan"
    error_message = "Plan role must be named <prefix>-github-plan."
  }

  assert {
    condition     = aws_iam_role.deploy_dev.name == "budgetlens-github-deploy-dev"
    error_message = "Development deploy role must be named <prefix>-github-deploy-dev."
  }

  assert {
    condition     = aws_iam_role.deploy_prod.name == "budgetlens-github-deploy-prod"
    error_message = "Production deploy role must be named <prefix>-github-deploy-prod."
  }

  assert {
    condition     = aws_iam_role.plan.max_session_duration == 3600
    error_message = "OIDC sessions must be short (3600 seconds)."
  }
}
