terraform {
  backend "s3" {
    key          = "budgetlens/bootstrap/terraform.tfstate"
    use_lockfile = true
    encrypt      = true
  }
}
