mock_provider "aws" {
  mock_data "aws_region" {
    defaults = {
      name   = "us-east-1"
      region = "us-east-1"
    }
  }
}

variables {
  name_prefix             = "budgetlens-dev"
  callback_urls           = ["https://localhost/login"]
  logout_urls             = ["https://localhost/"]
  mfa_configuration       = "OPTIONAL"
  allow_self_registration = false
  deletion_protection     = false
}

run "public_pkce_client_without_secret" {
  command = plan

  assert {
    condition     = aws_cognito_user_pool_client.web.generate_secret == false
    error_message = "The web client must be public PKCE without a client secret."
  }

  assert {
    condition     = aws_cognito_user_pool.this.name == "budgetlens-dev"
    error_message = "User pool name must be the environment name prefix."
  }
}

run "reject_http_callback" {
  command = plan

  variables {
    callback_urls = ["http://localhost/login"]
  }

  expect_failures = [
    var.callback_urls,
  ]
}
