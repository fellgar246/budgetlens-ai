provider "aws" {
  region              = var.aws_region
  allowed_account_ids = var.aws_account_id == "" ? null : [var.aws_account_id]

  default_tags {
    tags = {
      Project            = "BudgetLens"
      Environment        = "bootstrap"
      ManagedBy          = "Terraform"
      Owner              = var.owner
      CostCenter         = var.cost_center
      DataClassification = "financial-demo"
    }
  }
}
