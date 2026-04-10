# ============================================================================
# ECS Module
# Creates the ECS Fargate cluster, service, task definition, IAM roles,
# and supporting resources needed to run the containerised application
# ============================================================================

# ECS cluster - logical grouping of tasks and services
resource "aws_ecs_cluster" "main" {
  # Cluster name used in AWS console and CLI commands
  name = "${var.app_name}-cluster"

  # Container Insights provides monitoring metrics for containers
  # Disabled to reduce CloudWatch costs - enable for debugging
  setting {
    name  = "containerInsights"
    value = "disabled"
  }

  # Tags for resource identification
  tags = {
    Name = "${var.app_name}-cluster"
  }
}

# Configure capacity providers for the cluster
# Capacity providers determine how tasks are launched (Fargate vs EC2)
resource "aws_ecs_cluster_capacity_providers" "main" {
  # Attach to our cluster
  cluster_name = aws_ecs_cluster.main.name

  # Enable both Fargate and Fargate Spot capacity providers
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  # Default strategy: use Fargate Spot for cost savings (~70% cheaper)
  # Spot tasks may be interrupted but are ideal for stateless web apps
  default_capacity_provider_strategy {
    # Base count of tasks that must use this provider (0 = no minimum)
    base = 0
    # Weight determines proportion of tasks using this provider
    weight = 100
    # Use Spot instances by default for significant cost reduction
    capacity_provider = "FARGATE_SPOT"
  }
}

# CloudWatch Log Group for container logs
# ECS tasks send stdout/stderr here for monitoring and debugging
resource "aws_cloudwatch_log_group" "ecs" {
  # Log group name following the /ecs/<app> convention
  name = "/ecs/${var.app_name}"
  # Retain logs for 7 days to control CloudWatch storage costs
  retention_in_days = 7

  # Tags for resource identification
  tags = {
    Name = "${var.app_name}-logs"
  }
}

# ============================================================================
# IAM Roles - ECS requires two roles:
# 1. Task Execution Role: Used by ECS agent to pull images and start tasks
# 2. Task Role: Used by the running container to access AWS services
# ============================================================================

# Task Execution Role - allows the ECS agent to:
# - Pull Docker images from ECR
# - Write logs to CloudWatch
# - Retrieve secrets from Secrets Manager
resource "aws_iam_role" "ecs_task_execution" {
  # Role name for identification
  name = "${var.app_name}-ecs-task-execution-role"

  # Trust policy: only ECS tasks service can assume this role
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          # The ECS tasks service principal
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

# Attach the AWS-managed ECS task execution policy
# This grants permissions for ECR image pulls and CloudWatch log writes
resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  # Attach to our task execution role
  role = aws_iam_role.ecs_task_execution.name
  # AWS-managed policy that covers standard ECS task execution needs
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Custom inline policy granting access to specific Secrets Manager secrets
# The ECS agent needs this to inject secrets into the container at startup
resource "aws_iam_role_policy" "ecs_task_execution_secrets" {
  # Policy name for identification
  name = "${var.app_name}-ecs-secrets-policy"
  # Attach to the task execution role
  role = aws_iam_role.ecs_task_execution.id

  # Policy document granting read access to specific secrets
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          # Permission to read secret values
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          # Only allow access to the specific secrets needed by the app
          var.db_credentials_secret_arn,
          var.database_url_secret_arn,
          aws_secretsmanager_secret.jwt_secret.arn
        ]
      }
    ]
  })
}

# Task Role - used by the running application container
# Currently minimal - add permissions here if the app needs AWS API access
resource "aws_iam_role" "ecs_task" {
  # Role name for identification
  name = "${var.app_name}-ecs-task-role"

  # Trust policy: only ECS tasks service can assume this role
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          # The ECS tasks service principal
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

# ============================================================================
# JWT Secret - used by the application for signing authentication tokens
# ============================================================================

# Generate a cryptographically random 64-character string for JWT signing
resource "random_password" "jwt_secret" {
  # 64 characters provides strong entropy for HMAC-SHA256 signing
  length = 64
  # No special characters to avoid encoding issues
  special = false
}

# Store the JWT secret in Secrets Manager for secure retrieval by ECS
resource "aws_secretsmanager_secret" "jwt_secret" {
  # Secret name following the namespaced pattern
  name = "${var.app_name}/jwt-secret"
  # Immediate deletion allowed for clean re-creation after destroy
  recovery_window_in_days = 0
}

# Store the actual JWT secret value
resource "aws_secretsmanager_secret_version" "jwt_secret" {
  # Reference the secret created above
  secret_id = aws_secretsmanager_secret.jwt_secret.id
  # The randomly generated JWT signing key
  secret_string = random_password.jwt_secret.result
}

# ============================================================================
# ECS Task Definition
# Defines how the container should run: image, ports, env vars, resources
# ============================================================================
resource "aws_ecs_task_definition" "app" {
  # Task family name - used to group revisions of the same task
  family = "${var.app_name}-service"
  # awsvpc mode gives each task its own ENI and private IP address
  network_mode = "awsvpc"
  # This task runs on Fargate (serverless containers)
  requires_compatibilities = ["FARGATE"]
  # CPU units allocated to the task (256 = 0.25 vCPU)
  cpu = var.container_cpu
  # Memory in MB allocated to the task
  memory = var.container_memory
  # Role used by ECS agent to pull images, write logs, read secrets
  execution_role_arn = aws_iam_role.ecs_task_execution.arn
  # Role available to the running application container
  task_role_arn = aws_iam_role.ecs_task.arn

  # Container definitions specify what containers run in this task
  container_definitions = jsonencode([
    {
      # Container name - must match the container_name in load_balancer config
      name = var.app_name
      # Docker image to run (from ECR, tagged as "latest")
      image = "${var.ecr_repository_url}:latest"

      # Port mapping: expose the container port to the task's network interface
      portMappings = [
        {
          # Port the application listens on inside the container
          containerPort = var.container_port
          # Protocol for the port mapping
          protocol = "tcp"
        }
      ]

      # Environment variables passed directly to the container
      environment = [
        {
          # Indicates the deployment environment (prod, staging, dev)
          name  = "APP_ENV"
          value = var.environment
        },
        {
          # Seed demo data on first startup (creates demo users)
          name  = "SEED_DEMO_DATA"
          value = "true"
        }
      ]

      # Secrets are injected from AWS Secrets Manager at container startup
      # The ECS agent retrieves the secret value and sets it as an env var
      secrets = [
        {
          # DATABASE_URL env var - full PostgreSQL connection string
          name      = "DATABASE_URL"
          valueFrom = var.database_url_secret_arn
        },
        {
          # JWT_SECRET_KEY env var - used for signing auth tokens
          name      = "JWT_SECRET_KEY"
          valueFrom = aws_secretsmanager_secret.jwt_secret.arn
        }
      ]

      # Configure container logging to send stdout/stderr to CloudWatch
      logConfiguration = {
        # Use the awslogs driver to send logs to CloudWatch
        logDriver = "awslogs"
        options = {
          # CloudWatch log group to write to
          "awslogs-group" = aws_cloudwatch_log_group.ecs.name
          # AWS region for the log group
          "awslogs-region" = var.aws_region
          # Prefix for log stream names (helps identify which task wrote the log)
          "awslogs-stream-prefix" = "ecs"
        }
      }

      # Container-level health check (separate from ALB health check)
      # ECS uses this to determine if the container is healthy
      healthCheck = {
        # Command to run inside the container to check health
        command = ["CMD-SHELL", "curl -f http://localhost:${var.container_port}/health || exit 1"]
        # Seconds between health check executions
        interval = 30
        # Seconds before the health check times out
        timeout = 5
        # Number of consecutive failures before marking unhealthy
        retries = 3
        # Grace period in seconds before health checks start (allows app to boot)
        startPeriod = 60
      }
    }
  ])

  # Tags for resource identification
  tags = {
    Name = "${var.app_name}-task-definition"
  }
}

# ============================================================================
# ECS Service
# Manages the desired number of running tasks and integrates with the ALB
# ============================================================================
resource "aws_ecs_service" "app" {
  # Service name used in the AWS console and CLI
  name = "${var.app_name}-service"
  # Place the service in our cluster
  cluster = aws_ecs_cluster.main.id
  # The task definition that specifies what to run
  task_definition = aws_ecs_task_definition.app.arn
  # Number of task instances to keep running
  desired_count = var.desired_count

  # Use Fargate Spot for cost savings (up to 70% cheaper than on-demand)
  capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 100
  }

  # Network configuration for awsvpc mode
  network_configuration {
    # Place tasks in public subnets (NAT Gateway removed for cost savings)
    subnets = var.ecs_subnets
    # Attach the ECS security group to control traffic (only allows ALB inbound)
    security_groups = [var.ecs_security_group_id]
    # Public IP required for tasks to reach ECR, CloudWatch, Secrets Manager
    assign_public_ip = true
  }

  # Register tasks with the ALB target group for load balancing
  load_balancer {
    # Target group where ECS registers task IPs
    target_group_arn = var.target_group_arn
    # Must match the container name in the task definition
    container_name = var.app_name
    # Must match the container port in the task definition
    container_port = var.container_port
  }

  # Rolling deployment settings
  # Maximum 200% means a full new set of tasks starts before old ones stop
  deployment_maximum_percent = 200
  # Minimum 100% means old tasks stay running until new ones are healthy
  deployment_minimum_healthy_percent = 100

  # Ensure the HTTPS listener exists before creating the service
  # Otherwise ECS can't register targets with the ALB
  depends_on = [var.https_listener_arn]

  # Tags for resource identification
  tags = {
    Name = "${var.app_name}-service"
  }
}
