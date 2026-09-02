data "aws_region" "current" {}

data "aws_partition" "current" {}

data "aws_ec2_managed_prefix_list" "cloudfront" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
}

locals {
  bedrock_enabled   = var.ai_provider == "bedrock" && trimspace(var.bedrock_model_id) != ""
  bedrock_model_arn = local.bedrock_enabled ? "arn:${data.aws_partition.current.partition}:bedrock:${var.bedrock_region}::foundation-model/${var.bedrock_model_id}" : ""
  api_environment = [
    { name = "APP_ENV", value = var.environment },
    { name = "APP_LOG_LEVEL", value = "INFO" },
    { name = "AUTH_MODE", value = "oidc" },
    { name = "OBJECT_STORAGE_BACKEND", value = "s3" },
    { name = "S3_BUCKET", value = var.data_bucket_id },
    { name = "S3_REGION", value = var.aws_region },
    { name = "OIDC_ISSUER", value = var.oidc_issuer },
    { name = "OIDC_AUDIENCE", value = var.oidc_audience },
    { name = "OIDC_JWKS_URL", value = var.oidc_jwks_url },
    { name = "AI_PROVIDER", value = var.ai_provider },
    { name = "BEDROCK_REGION", value = var.bedrock_region },
    { name = "BEDROCK_MODEL_ID", value = var.bedrock_model_id },
    { name = "CORS_ORIGINS", value = var.cors_origins },
    { name = "DATABASE_RUNTIME_ROLE", value = "budgetlens_app" },
    { name = "IMPORT_EXECUTOR", value = "inline" },
    { name = "CONVERSATION_CONTENT_MODE", value = "redacted" },
    { name = "RUN_MIGRATIONS_ON_START", value = "0" },
    { name = "LOCAL_STORAGE_PATH", value = "/tmp/budgetlens-storage" },
  ]
  api_secrets = [
    { name = "DATABASE_URL", valueFrom = "${var.app_secret_arn}:DATABASE_URL::" },
    { name = "STORAGE_KEY_PEPPER", valueFrom = "${var.app_secret_arn}:STORAGE_KEY_PEPPER::" },
  ]
}

resource "aws_security_group" "alb" {
  name        = "${var.name_prefix}-alb"
  description = "CloudFront to ALB for ${var.name_prefix}"
  vpc_id      = var.vpc_id

  tags = {
    Name = "${var.name_prefix}-alb"
  }
}

resource "aws_vpc_security_group_ingress_rule" "alb_http_cloudfront" {
  # checkov:skip=CKV_AWS_260: Ingress is the CloudFront managed prefix list, not 0.0.0.0/0.
  security_group_id = aws_security_group.alb.id
  description       = "HTTP from CloudFront prefix list"
  prefix_list_id    = data.aws_ec2_managed_prefix_list.cloudfront.id
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "alb_to_ecs" {
  security_group_id            = aws_security_group.alb.id
  description                  = "Forward to API tasks"
  referenced_security_group_id = aws_security_group.ecs.id
  from_port                    = 8000
  to_port                      = 8000
  ip_protocol                  = "tcp"
}

resource "aws_security_group" "ecs" {
  name        = "${var.name_prefix}-ecs"
  description = "ECS tasks for ${var.name_prefix}"
  vpc_id      = var.vpc_id

  tags = {
    Name = "${var.name_prefix}-ecs"
  }
}

resource "aws_vpc_security_group_ingress_rule" "ecs_from_alb" {
  security_group_id            = aws_security_group.ecs.id
  description                  = "API port from ALB"
  referenced_security_group_id = aws_security_group.alb.id
  from_port                    = 8000
  to_port                      = 8000
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "ecs_https" {
  # Required for ECR, Secrets Manager, Bedrock, and S3 unless interface endpoints replace NAT.
  security_group_id = aws_security_group.ecs.id
  description       = "HTTPS to AWS APIs and the public internet via NAT"
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "ecs_to_rds" {
  security_group_id            = aws_security_group.ecs.id
  description                  = "PostgreSQL to the environment RDS"
  referenced_security_group_id = var.rds_security_group_id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "rds_from_ecs" {
  security_group_id            = var.rds_security_group_id
  description                  = "PostgreSQL from ${var.name_prefix} ECS tasks"
  referenced_security_group_id = aws_security_group.ecs.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
}

resource "aws_cloudwatch_log_group" "api" {
  # checkov:skip=CKV_AWS_338: Retention follows the environment log policy.
  name              = "/budgetlens/${var.environment}/api"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.kms_key_arn
}

resource "aws_cloudwatch_log_group" "ops" {
  # checkov:skip=CKV_AWS_338: Retention follows the environment log policy.
  name              = "/budgetlens/${var.environment}/ops"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.kms_key_arn
}

data "aws_iam_policy_document" "ecs_tasks_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "execution" {
  name               = "${var.name_prefix}-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume.json
}

data "aws_iam_policy_document" "execution" {
  statement {
    sid    = "EcrAuth"
    effect = "Allow"
    actions = [
      "ecr:GetAuthorizationToken",
    ]
    # GetAuthorizationToken does not support resource-level permissions.
    resources = ["*"]
  }

  statement {
    sid    = "EcrPull"
    effect = "Allow"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
    ]
    resources = [var.ecr_repository_arn]
  }

  statement {
    sid    = "WriteLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = [
      "${aws_cloudwatch_log_group.api.arn}:*",
      "${aws_cloudwatch_log_group.ops.arn}:*",
    ]
  }

  statement {
    sid       = "ReadSecrets"
    effect    = "Allow"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [var.app_secret_arn]
  }

  statement {
    sid    = "DecryptSecrets"
    effect = "Allow"
    actions = [
      "kms:Decrypt",
      "kms:DescribeKey",
    ]
    resources = [var.kms_key_arn]
  }
}

resource "aws_iam_role_policy" "execution" {
  name   = "${var.name_prefix}-execution"
  role   = aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.execution.json
}

resource "aws_iam_role" "task" {
  name               = "${var.name_prefix}-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume.json
}

data "aws_iam_policy_document" "task" {
  statement {
    sid    = "DataBucketObjects"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:AbortMultipartUpload",
    ]
    resources = ["${var.data_bucket_arn}/*"]
  }

  statement {
    sid       = "DataBucketList"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [var.data_bucket_arn]
  }

  statement {
    sid    = "DataBucketEncryption"
    effect = "Allow"
    actions = [
      "kms:Decrypt",
      "kms:DescribeKey",
      "kms:Encrypt",
      "kms:GenerateDataKey",
    ]
    resources = [var.kms_key_arn]
  }

  dynamic "statement" {
    for_each = local.bedrock_enabled ? [1] : []
    content {
      sid    = "BedrockConverse"
      effect = "Allow"
      actions = [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:Converse",
        "bedrock:ConverseStream",
      ]
      resources = [local.bedrock_model_arn]
    }
  }
}

resource "aws_iam_role_policy" "task" {
  name   = "${var.name_prefix}-task"
  role   = aws_iam_role.task.id
  policy = data.aws_iam_policy_document.task.json
}

resource "aws_iam_role" "migration" {
  name               = "${var.name_prefix}-migration"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume.json
}

data "aws_iam_policy_document" "migration" {
  statement {
    sid       = "NoRuntimeAwsApis"
    effect    = "Deny"
    actions   = ["s3:*", "bedrock:*"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "migration" {
  name   = "${var.name_prefix}-migration"
  role   = aws_iam_role.migration.id
  policy = data.aws_iam_policy_document.migration.json
}

resource "aws_lb" "api" {
  # checkov:skip=CKV_AWS_91: Access logs are optional and gated by enable_alb_access_logs.
  # checkov:skip=CKV_AWS_150: Deletion protection is environment-driven; production enables it.
  # checkov:skip=CKV2_AWS_20: CloudFront terminates TLS; ALB accepts HTTP only from the CloudFront prefix list.
  # checkov:skip=CKV_AWS_2: Same CloudFront-origin design; no public HTTP on the internet.
  # checkov:skip=CKV2_AWS_28: WAF attaches at CloudFront, not on this regional ALB.
  name                       = "${var.name_prefix}-alb"
  internal                   = false
  load_balancer_type         = "application"
  security_groups            = [aws_security_group.alb.id]
  subnets                    = var.public_subnet_ids
  drop_invalid_header_fields = true
  desync_mitigation_mode     = "strictest"
  idle_timeout               = 120
  enable_deletion_protection = var.alb_deletion_protection

  dynamic "access_logs" {
    for_each = var.enable_alb_access_logs ? [1] : []
    content {
      bucket  = var.logs_bucket_id
      prefix  = "alb"
      enabled = true
    }
  }
}

resource "aws_lb_target_group" "api" {
  # checkov:skip=CKV_AWS_378: Targets are private Fargate tasks; TLS terminates at CloudFront.
  name        = "${var.name_prefix}-api"
  port        = 8000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id

  health_check {
    enabled             = true
    path                = "/api/v1/health/ready"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  deregistration_delay = 30
}

resource "aws_lb_listener" "http" {
  # checkov:skip=CKV_AWS_2: Listener is reachable only from CloudFront. HTTPS is on the distribution.
  # checkov:skip=CKV_AWS_103: TLS is terminated at CloudFront.
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

resource "aws_ecs_cluster" "this" {
  # checkov:skip=CKV_AWS_65: Container Insights is opt-in after a cost review.
  name = var.name_prefix

  setting {
    name  = "containerInsights"
    value = var.enable_container_insights ? "enabled" : "disabled"
  }
}

resource "aws_ecs_cluster_capacity_providers" "this" {
  cluster_name = aws_ecs_cluster.this.name

  capacity_providers = ["FARGATE"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
  }
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${var.name_prefix}-api"
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([
    {
      name      = "api"
      image     = var.api_image
      essential = true
      command   = ["api"]
      user      = "10001"
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]
      environment            = local.api_environment
      secrets                = local.api_secrets
      readonlyRootFilesystem = true
      linuxParameters = {
        tmpfs = [
          {
            containerPath = "/tmp"
            size          = 256
          }
        ]
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.api.name
          awslogs-region        = data.aws_region.current.region
          awslogs-stream-prefix = "api"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/live', timeout=2)\""]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 40
      }
    }
  ])
}

resource "aws_ecs_task_definition" "migrate" {
  family                   = "${var.name_prefix}-migrate"
  cpu                      = 256
  memory                   = 512
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.migration.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([
    {
      name                   = "migrate"
      image                  = var.api_image
      essential              = true
      command                = ["migrate"]
      user                   = "10001"
      environment            = local.api_environment
      secrets                = local.api_secrets
      readonlyRootFilesystem = true
      linuxParameters = {
        tmpfs = [
          {
            containerPath = "/tmp"
            size          = 64
          }
        ]
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ops.name
          awslogs-region        = data.aws_region.current.region
          awslogs-stream-prefix = "migrate"
        }
      }
    }
  ])
}

resource "aws_ecs_task_definition" "ops" {
  family                   = "${var.name_prefix}-ops"
  cpu                      = 256
  memory                   = 512
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([
    {
      name                   = "ops"
      image                  = var.api_image
      essential              = true
      command                = ["watchdog"]
      user                   = "10001"
      environment            = local.api_environment
      secrets                = local.api_secrets
      readonlyRootFilesystem = true
      linuxParameters = {
        tmpfs = [
          {
            containerPath = "/tmp"
            size          = 64
          }
        ]
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ops.name
          awslogs-region        = data.aws_region.current.region
          awslogs-stream-prefix = "ops"
        }
      }
    }
  ])
}

resource "aws_ecs_task_definition" "seed" {
  count                    = var.create_seed_task ? 1 : 0
  family                   = "${var.name_prefix}-seed"
  cpu                      = 256
  memory                   = 512
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([
    {
      name                   = "seed"
      image                  = var.api_image
      essential              = true
      command                = ["seed"]
      user                   = "10001"
      environment            = local.api_environment
      secrets                = local.api_secrets
      readonlyRootFilesystem = true
      linuxParameters = {
        tmpfs = [
          {
            containerPath = "/tmp"
            size          = 64
          }
        ]
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ops.name
          awslogs-region        = data.aws_region.current.region
          awslogs-stream-prefix = "seed"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "api" {
  # checkov:skip=CKV_AWS_332: Platform 1.4.0 is the pinned Fargate version; image tags stay immutable.
  name                               = "${var.name_prefix}-api"
  cluster                            = aws_ecs_cluster.this.id
  task_definition                    = aws_ecs_task_definition.api.arn
  desired_count                      = var.api_desired_count
  launch_type                        = "FARGATE"
  platform_version                   = "1.4.0"
  enable_execute_command             = false
  health_check_grace_period_seconds  = 60
  deployment_minimum_healthy_percent = var.api_desired_count > 1 ? 50 : 0
  deployment_maximum_percent         = 200

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

}

resource "aws_appautoscaling_target" "api" {
  count              = var.enable_autoscaling ? 1 : 0
  max_capacity       = max(var.autoscaling_max_count, var.api_desired_count)
  min_capacity       = var.api_desired_count
  resource_id        = "service/${aws_ecs_cluster.this.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "api_cpu" {
  count              = var.enable_autoscaling ? 1 : 0
  name               = "${var.name_prefix}-api-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api[0].resource_id
  scalable_dimension = aws_appautoscaling_target.api[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.api[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
