data "aws_cloudfront_cache_policy" "caching_optimized" {
  name = "Managed-CachingOptimized"
}

data "aws_cloudfront_cache_policy" "caching_disabled" {
  name = "Managed-CachingDisabled"
}

data "aws_cloudfront_origin_request_policy" "all_viewer_except_host" {
  name = "Managed-AllViewerExceptHostHeader"
}

data "aws_cloudfront_origin_request_policy" "cors_s3" {
  name = "Managed-CORS-S3Origin"
}

resource "aws_cloudfront_origin_access_control" "web" {
  name                              = "${var.name_prefix}-web"
  description                       = "Origin access control for the ${var.name_prefix} web bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_acm_certificate" "cdn" {
  count = var.domain_name == "" ? 0 : 1

  provider          = aws.us_east_1
  domain_name       = var.domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "certificate" {
  for_each = var.create_dns_records && var.domain_name != "" ? {
    for option in aws_acm_certificate.cdn[0].domain_validation_options : option.domain_name => option
  } : {}

  zone_id         = var.hosted_zone_id
  name            = each.value.resource_record_name
  type            = each.value.resource_record_type
  ttl             = 60
  records         = [each.value.resource_record_value]
  allow_overwrite = true
}

resource "aws_acm_certificate_validation" "cdn" {
  count = var.create_dns_records && var.domain_name != "" ? 1 : 0

  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.cdn[0].arn
  validation_record_fqdns = [for record in aws_route53_record.certificate : record.fqdn]
}

resource "aws_cloudfront_response_headers_policy" "security" {
  name    = "${var.name_prefix}-security"
  comment = "Security headers for ${var.name_prefix}"

  security_headers_config {
    content_type_options {
      override = true
    }

    frame_options {
      frame_option = "DENY"
      override     = true
    }

    referrer_policy {
      referrer_policy = "same-origin"
      override        = true
    }

    strict_transport_security {
      access_control_max_age_sec = 31536000
      include_subdomains         = true
      preload                    = true
      override                   = true
    }

    xss_protection {
      protection = true
      mode_block = true
      override   = true
    }

    content_security_policy {
      content_security_policy = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' https://*.amazoncognito.com https://cognito-idp.*.amazonaws.com; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
      override                = true
    }
  }

  custom_headers_config {
    items {
      header   = "permissions-policy"
      override = true
      value    = "camera=(), microphone=(), geolocation=()"
    }
  }
}

resource "aws_cloudfront_distribution" "this" {
  # checkov:skip=CKV_AWS_68: WAF is optional and attached when waf_web_acl_arn is set.
  # checkov:skip=CKV_AWS_86: Access logging is optional and gated by enable_access_logs.
  # checkov:skip=CKV_AWS_174: Default CloudFront certificates cannot set TLSv1.2_2021; custom domains do.
  # checkov:skip=CKV_AWS_310: Origin failover is omitted for a single-origin demo.
  # checkov:skip=CKV_AWS_374: Geo restriction is omitted for a demonstration distribution.
  # checkov:skip=CKV2_AWS_42: A custom certificate is created only when domain_name is set.
  # checkov:skip=CKV2_AWS_47: WAF association is environment-driven.
  enabled             = true
  comment             = var.name_prefix
  http_version        = "http2and3"
  is_ipv6_enabled     = true
  price_class         = var.price_class
  wait_for_deployment = false
  web_acl_id          = var.waf_web_acl_arn == "" ? null : var.waf_web_acl_arn
  aliases             = var.domain_name == "" ? [] : [var.domain_name]

  origin {
    domain_name              = var.web_bucket_regional_domain_name
    origin_id                = "web"
    origin_access_control_id = aws_cloudfront_origin_access_control.web.id
  }

  origin {
    domain_name = var.alb_dns_name
    origin_id   = "api"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id           = "web"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD", "OPTIONS"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = data.aws_cloudfront_cache_policy.caching_optimized.id
    origin_request_policy_id   = data.aws_cloudfront_origin_request_policy.cors_s3.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
  }

  ordered_cache_behavior {
    path_pattern               = "/api/*"
    target_origin_id           = "api"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = data.aws_cloudfront_cache_policy.caching_disabled.id
    origin_request_policy_id   = data.aws_cloudfront_origin_request_policy.all_viewer_except_host.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
  }

  ordered_cache_behavior {
    path_pattern               = "/_next/static/*"
    target_origin_id           = "web"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD", "OPTIONS"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = data.aws_cloudfront_cache_policy.caching_optimized.id
    origin_request_policy_id   = data.aws_cloudfront_origin_request_policy.cors_s3.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = var.domain_name == ""
    acm_certificate_arn            = var.domain_name == "" ? null : (var.create_dns_records ? aws_acm_certificate_validation.cdn[0].certificate_arn : aws_acm_certificate.cdn[0].arn)
    ssl_support_method             = var.domain_name == "" ? null : "sni-only"
    # Default CloudFront certificates only accept the legacy minimum. Custom domains use TLSv1.2_2021.
    minimum_protocol_version = var.domain_name == "" ? "TLSv1" : "TLSv1.2_2021"
  }

  default_root_object = "index.html"

  custom_error_response {
    error_code            = 403
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 10
  }

  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 10
  }
}

check "dns_inputs" {
  assert {
    condition     = !var.create_dns_records || (var.domain_name != "" && var.hosted_zone_id != "")
    error_message = "create_dns_records requires domain_name and hosted_zone_id."
  }
}

data "aws_iam_policy_document" "web_oac" {
  statement {
    sid     = "DenyInsecureTransport"
    effect  = "Deny"
    actions = ["s3:*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    resources = [
      var.web_bucket_arn,
      "${var.web_bucket_arn}/*",
    ]
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }

  statement {
    sid     = "AllowCloudFrontRead"
    effect  = "Allow"
    actions = ["s3:GetObject"]
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    resources = ["${var.web_bucket_arn}/*"]
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.this.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "web_oac" {
  bucket = var.web_bucket_id
  policy = data.aws_iam_policy_document.web_oac.json
}

resource "aws_route53_record" "app" {
  count = var.create_dns_records && var.domain_name != "" ? 1 : 0

  zone_id = var.hosted_zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.this.domain_name
    zone_id                = aws_cloudfront_distribution.this.hosted_zone_id
    evaluate_target_health = false
  }
}
