# network

Creates one VPC per environment with two or three Availability Zones.

- Public subnets for the load balancer and NAT gateways
- Private subnets for ECS tasks
- Isolated subnets for RDS (no internet route)
- One NAT Gateway in development, or one per AZ when `nat_gateway_count` matches the AZ count
- A free S3 gateway endpoint on every route table
- Optional interface endpoints and VPC flow logs

## Example

```hcl
module "network" {
  source = "../../modules/network"

  name_prefix                 = "budgetlens-dev"
  vpc_cidr                    = "10.40.0.0/16"
  availability_zone_count     = 2
  nat_gateway_count           = 1
  enable_vpc_flow_logs        = false
  enable_interface_endpoints  = false
  flow_log_retention_days     = 14
  kms_key_arn                 = module.security.kms_key_arn
}
```
