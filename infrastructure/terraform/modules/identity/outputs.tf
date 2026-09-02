locals {
  issuer = "https://cognito-idp.${data.aws_region.current.region}.amazonaws.com/${aws_cognito_user_pool.this.id}"
}

output "user_pool_id" {
  description = "Cognito user pool ID."
  value       = aws_cognito_user_pool.this.id
}

output "user_pool_arn" {
  description = "Cognito user pool ARN."
  value       = aws_cognito_user_pool.this.arn
}

output "client_id" {
  description = "Public app client ID used as the OIDC audience. No client secret is created."
  value       = aws_cognito_user_pool_client.web.id
}

output "issuer" {
  description = "OIDC issuer URL."
  value       = local.issuer
}

output "jwks_url" {
  description = "OIDC JWKS URL."
  value       = "${local.issuer}/.well-known/jwks.json"
}

output "hosted_ui_domain" {
  description = "Cognito hosted UI domain (without scheme)."
  value       = "${aws_cognito_user_pool_domain.this.domain}.auth.${data.aws_region.current.region}.amazoncognito.com"
}

output "hosted_ui_url" {
  description = "Cognito hosted UI base URL."
  value       = "https://${aws_cognito_user_pool_domain.this.domain}.auth.${data.aws_region.current.region}.amazoncognito.com"
}
