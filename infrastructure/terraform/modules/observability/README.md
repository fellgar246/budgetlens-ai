# observability

Creates an SNS topic, calibrated CloudWatch alarms, and an operator dashboard.

Alarms are tagged with `FailureClass` values `application`, `dependency`, or `infrastructure`. Thresholds are variables and should be tuned after load tests.

An email subscription, when configured, is not treated as confirmed by Terraform.

## Example

```hcl
module "observability" {
  source = "../../modules/observability"

  name_prefix     = "budgetlens-dev"
  alarm_email     = ""
  alb_arn_suffix  = module.compute.alb_arn
  cluster_name    = module.compute.cluster_name
  service_name    = module.compute.service_name
  rds_identifier  = module.database.identifier
  api_desired_count = 1
}
```
