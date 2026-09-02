terraform {
  backend "s3" {
    key          = "budgetlens/prod/terraform.tfstate"
    use_lockfile = true
    encrypt      = true
  }
}
