resource "random_password" "django_secret_key" {
  length  = 64
  special = false
}

resource "aws_secretsmanager_secret" "django_secret_key" {
  name                    = "${var.name_prefix}/django-secret-key"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "django_secret_key" {
  secret_id     = aws_secretsmanager_secret.django_secret_key.id
  secret_string = random_password.django_secret_key.result
}

resource "aws_security_group" "load_balancer" {
  name_prefix = "${var.name_prefix}-alb-"
  description = "Acceso HTTP público al balanceador."
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "task" {
  name_prefix = "${var.name_prefix}-task-"
  description = "Acepta tráfico de aplicación únicamente desde el ALB."
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.load_balancer.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_lb" "web" {
  name               = substr("${var.name_prefix}-alb", 0, 32)
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.load_balancer.id]
  subnets            = var.public_subnet_ids
}

resource "aws_lb_target_group" "web" {
  name        = substr("${var.name_prefix}-web", 0, 32)
  port        = 8000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id

  health_check {
    path                = "/"
    matcher             = "200-399"
    interval            = 30
    healthy_threshold   = 2
    unhealthy_threshold = 5
  }
}

resource "aws_lb_listener" "web" {
  load_balancer_arn = aws_lb.web.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }
}

resource "aws_iam_role" "task_execution" {
  name = "${var.name_prefix}-ecs-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "task_execution" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "secrets" {
  name = "${var.name_prefix}-read-secrets"
  role = aws_iam_role.task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [var.db_password_secret_arn, aws_secretsmanager_secret.django_secret_key.arn]
    }]
  })
}

resource "aws_ecs_cluster" "main" {
  name = "${var.name_prefix}-cluster"
}

resource "aws_ecs_task_definition" "web" {
  family                   = "${var.name_prefix}-web"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.task_execution.arn

  container_definitions = jsonencode([{
    name      = "healthchecks"
    image     = "healthchecks/healthchecks:${var.image_tag}"
    essential = true
    portMappings = [{
      containerPort = 8000
      hostPort      = 8000
      protocol      = "tcp"
    }]
    environment = [
      { name = "DB", value = "postgres" },
      { name = "DB_HOST", value = var.db_endpoint },
      { name = "DB_PORT", value = tostring(var.db_port) },
      { name = "DB_NAME", value = var.db_name },
      { name = "DB_USER", value = var.db_user },
      { name = "SITE_ROOT", value = "http://${aws_lb.web.dns_name}" },
      { name = "ALLOWED_HOSTS", value = aws_lb.web.dns_name }
    ]
    secrets = [
      { name = "DB_PASSWORD", valueFrom = var.db_password_secret_arn },
      { name = "SECRET_KEY", valueFrom = aws_secretsmanager_secret.django_secret_key.arn }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.web.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "healthchecks"
      }
    }
  }])

  depends_on = [aws_secretsmanager_secret_version.django_secret_key]
}

resource "aws_cloudwatch_log_group" "web" {
  name              = "/ecs/${var.name_prefix}"
  retention_in_days = 30
}

resource "aws_ecs_service" "web" {
  name            = "${var.name_prefix}-web"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.web.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = var.public_subnet_ids
    security_groups  = [aws_security_group.task.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.web.arn
    container_name   = "healthchecks"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.web, aws_iam_role_policy_attachment.task_execution, aws_iam_role_policy.secrets]
}
