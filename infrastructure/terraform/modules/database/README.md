# database

Creates a private PostgreSQL instance in isolated subnets, an explicit parameter group, and a generated Secrets Manager secret.

The master password is never a Terraform input or output. ECS injects `DATABASE_URL` and `STORAGE_KEY_PEPPER` from the secret ARN.

Development is single-AZ with a small instance class. Production enables Multi-AZ and deletion protection.

## Example

```hcl
module "database" {
  source = "../../modules/database"

  name_prefix                  = "budgetlens-dev"
  vpc_id                       = module.network.vpc_id
  isolated_subnet_ids          = module.network.isolated_subnet_ids
  kms_key_arn                  = module.security.kms_key_arn
  instance_class               = "db.t4g.micro"
  allocated_storage            = 20
  max_allocated_storage        = 50
  multi_az                     = false
  backup_retention_days        = 7
  deletion_protection          = false
  performance_insights         = false
  log_retention_days           = 14
  secret_recovery_window_days  = 0
}
```
