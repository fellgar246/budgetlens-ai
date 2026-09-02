mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = {
      account_id = "123456789012"
    }
  }

  mock_data "aws_iam_policy_document" {
    defaults = {
      json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Deny\",\"Action\":\"s3:*\",\"Resource\":\"*\"}]}"
    }
  }
}

variables {
  name_prefix                  = "budgetlens-dev"
  kms_key_arn                  = "arn:aws:kms:us-east-1:123456789012:key/test"
  enable_web_versioning        = false
  enable_data_versioning       = true
  enable_access_logs           = false
  cors_allowed_origins         = []
  original_file_retention_days = 90
  error_report_retention_days  = 30
  export_retention_days        = 1
}

run "keeps_application_buckets_private" {
  command = plan

  assert {
    condition     = aws_s3_bucket_public_access_block.web.block_public_acls == true
    error_message = "The web bucket must block public ACLs."
  }

  assert {
    condition     = aws_s3_bucket_public_access_block.data.block_public_acls == true
    error_message = "The data bucket must block public ACLs."
  }

  assert {
    condition     = aws_s3_bucket.web.force_destroy == false
    error_message = "Application buckets must not empty themselves on destroy."
  }
}
