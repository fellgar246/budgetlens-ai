terraform {
  backend "s3" {
    key          = "budgetlens/dev/terraform.tfstate"
    use_lockfile = true
    encrypt      = true
  }
}
