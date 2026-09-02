locals {
  repository   = "${var.github_owner}/${var.github_repository}"
  provider_arn = var.create_provider ? aws_iam_openid_connect_provider.github[0].arn : var.existing_provider_arn
}

resource "aws_iam_openid_connect_provider" "github" {
  count = var.create_provider ? 1 : 0

  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["d89e3bd43d5d909b47a18977aa9d5ce36cee184c"]
}

data "aws_iam_policy_document" "plan_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [local.provider_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:iss"
      values   = ["https://token.actions.githubusercontent.com"]
    }
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        "repo:${local.repository}:ref:refs/heads/main",
        "repo:${local.repository}:ref:refs/tags/v*",
        "repo:${local.repository}:pull_request",
        "repo:${local.repository}:environment:dev",
        "repo:${local.repository}:environment:prod",
      ]
    }
  }
}

data "aws_iam_policy_document" "deploy_dev_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [local.provider_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:iss"
      values   = ["https://token.actions.githubusercontent.com"]
    }
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        "repo:${local.repository}:ref:refs/heads/main",
        "repo:${local.repository}:ref:refs/tags/v*",
        "repo:${local.repository}:environment:dev",
      ]
    }
  }
}

data "aws_iam_policy_document" "deploy_prod_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [local.provider_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:iss"
      values   = ["https://token.actions.githubusercontent.com"]
    }
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        "repo:${local.repository}:environment:prod",
      ]
    }
  }
}

resource "aws_iam_role" "plan" {
  name                 = "${var.name_prefix}-github-plan"
  assume_role_policy   = data.aws_iam_policy_document.plan_trust.json
  max_session_duration = 3600
}

resource "aws_iam_role" "deploy_dev" {
  name                 = "${var.name_prefix}-github-deploy-dev"
  assume_role_policy   = data.aws_iam_policy_document.deploy_dev_trust.json
  max_session_duration = 3600
}

resource "aws_iam_role" "deploy_prod" {
  name                 = "${var.name_prefix}-github-deploy-prod"
  assume_role_policy   = data.aws_iam_policy_document.deploy_prod_trust.json
  max_session_duration = 3600
}

data "aws_iam_policy_document" "state" {
  statement {
    sid    = "StateBucket"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
    ]
    resources = [
      var.state_bucket_arn,
      "${var.state_bucket_arn}/*",
    ]
  }
}

resource "aws_iam_role_policy" "plan_state" {
  name   = "terraform-state"
  role   = aws_iam_role.plan.id
  policy = data.aws_iam_policy_document.state.json
}

resource "aws_iam_role_policy" "deploy_dev_state" {
  name   = "terraform-state"
  role   = aws_iam_role.deploy_dev.id
  policy = data.aws_iam_policy_document.state.json
}

resource "aws_iam_role_policy" "deploy_prod_state" {
  name   = "terraform-state"
  role   = aws_iam_role.deploy_prod.id
  policy = data.aws_iam_policy_document.state.json
}

resource "aws_iam_role_policy_attachment" "plan_readonly" {
  role       = aws_iam_role.plan.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}

data "aws_iam_policy_document" "deploy" {
  # checkov:skip=CKV_AWS_107: Deploy roles manage application services; IAM user creation is denied.
  # checkov:skip=CKV_AWS_108: Deploy roles are trusted only from the named GitHub repository and environment.
  # checkov:skip=CKV_AWS_109: Resource-level constraints are incomplete for these deploy APIs.
  # checkov:skip=CKV_AWS_110: Privilege is limited by OIDC trust conditions and a deny of IAM user keys.
  # checkov:skip=CKV_AWS_111: Deploy needs to create and update the environment resource set.
  # checkov:skip=CKV_AWS_356: Several AWS deploy APIs require Resource=*.
  statement {
    sid    = "ManageApplication"
    effect = "Allow"
    actions = [
      "acm:*",
      "application-autoscaling:*",
      "cloudfront:*",
      "cloudwatch:*",
      "cognito-idp:*",
      "ec2:*",
      "ecr:*",
      "ecs:*",
      "elasticloadbalancing:*",
      "events:*",
      "logs:*",
      "rds:*",
      "route53:ChangeResourceRecordSets",
      "route53:GetChange",
      "route53:GetHostedZone",
      "route53:ListHostedZones",
      "route53:ListResourceRecordSets",
      "s3:*",
      "secretsmanager:*",
      "sns:*",
      "ssm:GetParameter",
      "ssm:GetParameters",
      "wafv2:*",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ManageEncryptionKeys"
    effect = "Allow"
    actions = [
      "kms:CancelKeyDeletion",
      "kms:CreateAlias",
      "kms:CreateGrant",
      "kms:CreateKey",
      "kms:Decrypt",
      "kms:DeleteAlias",
      "kms:DescribeKey",
      "kms:EnableKeyRotation",
      "kms:Encrypt",
      "kms:GenerateDataKey*",
      "kms:GetKeyPolicy",
      "kms:GetKeyRotationStatus",
      "kms:ListAliases",
      "kms:ListKeys",
      "kms:ListResourceTags",
      "kms:PutKeyPolicy",
      "kms:ScheduleKeyDeletion",
      "kms:TagResource",
      "kms:UntagResource",
      "kms:UpdateAlias",
    ]
    # CreateKey and ListKeys do not support resource-level permissions.
    resources = ["*"]
  }

  statement {
    sid    = "CreateServiceLinkedRoles"
    effect = "Allow"
    actions = [
      "iam:CreateServiceLinkedRole",
    ]
    # CreateServiceLinkedRole is an account-level API; path/service is constrained below.
    resources = ["*"]
    condition {
      test     = "StringLike"
      variable = "iam:AWSServiceName"
      values = [
        "autoscaling.amazonaws.com",
        "ecs.amazonaws.com",
        "ecs.application-autoscaling.amazonaws.com",
        "elasticloadbalancing.amazonaws.com",
        "rds.amazonaws.com",
      ]
    }
  }

  statement {
    sid    = "ManagePrefixedRoles"
    effect = "Allow"
    actions = [
      "iam:AttachRolePolicy",
      "iam:CreateRole",
      "iam:DeleteRole",
      "iam:DeleteRolePolicy",
      "iam:GetRole",
      "iam:GetRolePolicy",
      "iam:ListAttachedRolePolicies",
      "iam:ListInstanceProfilesForRole",
      "iam:ListRolePolicies",
      "iam:PassRole",
      "iam:PutRolePolicy",
      "iam:TagRole",
      "iam:UntagRole",
      "iam:UpdateAssumeRolePolicy",
      "iam:UpdateRole",
      "iam:UpdateRoleDescription",
    ]
    resources = [
      "arn:aws:iam::*:role/${var.name_prefix}-*",
    ]
  }

  statement {
    sid    = "ReadManagedPolicies"
    effect = "Allow"
    actions = [
      "iam:GetPolicy",
      "iam:GetPolicyVersion",
    ]
    resources = [
      "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole",
    ]
  }

  statement {
    sid    = "DenyIamUserEscalation"
    effect = "Deny"
    actions = [
      "iam:CreateUser",
      "iam:CreateAccessKey",
      "iam:AttachUserPolicy",
      "iam:PutUserPolicy",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "DenyAssumeRolePolicyOutsidePrefix"
    effect = "Deny"
    actions = [
      "iam:UpdateAssumeRolePolicy",
    ]
    not_resources = [
      "arn:aws:iam::*:role/${var.name_prefix}-*",
    ]
  }
}

resource "aws_iam_role_policy" "deploy_dev" {
  # checkov:skip=CKV_AWS_290: Deploy needs to manage the environment resource set; IAM user creation is denied.
  # checkov:skip=CKV_AWS_355: AWS APIs for these services require * where resource-level constraints are incomplete.
  name   = "deploy"
  role   = aws_iam_role.deploy_dev.id
  policy = data.aws_iam_policy_document.deploy.json
}

resource "aws_iam_role_policy" "deploy_prod" {
  # checkov:skip=CKV_AWS_290: Deploy needs to manage the environment resource set; IAM user creation is denied.
  # checkov:skip=CKV_AWS_355: AWS APIs for these services require * where resource-level constraints are incomplete.
  name   = "deploy"
  role   = aws_iam_role.deploy_prod.id
  policy = data.aws_iam_policy_document.deploy.json
}
