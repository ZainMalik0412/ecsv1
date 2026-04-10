# ============================================================================
# ECS Module - Input Variables
# These variables configure the ECS cluster, service, and task definition
# ============================================================================

# Application name used as prefix for all ECS resource names
variable "app_name" {
  description = "Application name used for resource naming"
  type        = string
}

# Deployment environment identifier (prod, staging, dev)
variable "environment" {
  description = "Environment name (e.g. prod, staging)"
  type        = string
}

# AWS region used for CloudWatch log group configuration
variable "aws_region" {
  description = "AWS region for log group placement"
  type        = string
}

# Port the application container listens on
variable "container_port" {
  description = "Port exposed by the application container"
  type        = number
}

# CPU units for the Fargate task (256 = 0.25 vCPU, 512 = 0.5 vCPU, etc.)
variable "container_cpu" {
  description = "CPU units for the ECS task"
  type        = number
}

# Memory in MB for the Fargate task
variable "container_memory" {
  description = "Memory in MB for the ECS task"
  type        = number
}

# Number of task instances to run (1 for cost savings, 2+ for HA)
variable "desired_count" {
  description = "Desired number of running ECS tasks"
  type        = number
}

# Subnet IDs where ECS tasks are placed (public subnets to avoid NAT Gateway costs)
variable "ecs_subnets" {
  description = "List of subnet IDs for ECS task placement"
  type        = list(string)
}

# Security group ID controlling traffic to/from ECS tasks
variable "ecs_security_group_id" {
  description = "Security group ID for ECS tasks"
  type        = string
}

# ECR repository URL for the Docker image (e.g. 123456.dkr.ecr.region.amazonaws.com/app)
variable "ecr_repository_url" {
  description = "URL of the ECR repository containing the Docker image"
  type        = string
}

# ALB target group ARN where ECS registers task IPs for load balancing
variable "target_group_arn" {
  description = "ARN of the ALB target group"
  type        = string
}

# HTTPS listener ARN - ECS service depends on this existing first
variable "https_listener_arn" {
  description = "ARN of the ALB HTTPS listener (used for dependency ordering)"
  type        = string
}

# ARN of the database credentials secret in Secrets Manager
variable "db_credentials_secret_arn" {
  description = "ARN of the DB credentials secret in Secrets Manager"
  type        = string
}

# ARN of the DATABASE_URL secret in Secrets Manager
variable "database_url_secret_arn" {
  description = "ARN of the database URL secret in Secrets Manager"
  type        = string
}
