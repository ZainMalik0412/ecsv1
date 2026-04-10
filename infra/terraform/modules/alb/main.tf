# ============================================================================
# ALB Module
# Creates the Application Load Balancer, target group, and listeners
# The ALB distributes incoming HTTPS traffic to ECS Fargate tasks
# ============================================================================

# Application Load Balancer - the public entry point for all web traffic
resource "aws_lb" "main" {
  # Name of the load balancer (must be unique within the account/region)
  name = "${var.app_name}-alb"
  # Internet-facing ALB (not internal) so it's reachable from the internet
  internal = false
  # Application type supports HTTP/HTTPS routing (vs network LB for TCP/UDP)
  load_balancer_type = "application"
  # Attach the ALB security group to control inbound/outbound traffic
  security_groups = [var.alb_security_group_id]
  # Place the ALB in public subnets so it gets a public IP address
  subnets = var.public_subnets

  # Disable deletion protection so Terraform can destroy the ALB
  # Enable this in production if you want to prevent accidental deletion
  enable_deletion_protection = false

  # Tags for resource identification
  tags = {
    Name = "${var.app_name}-alb"
  }
}

# Target group defines where the ALB forwards traffic to
# ECS registers its tasks as targets in this group
resource "aws_lb_target_group" "app" {
  # Include port in name to allow blue-green deployments with different ports
  name = "${var.app_name}-tg-${var.container_port}"
  # Port that the targets (ECS tasks) listen on
  port = var.container_port
  # Protocol used to communicate with targets
  protocol = "HTTP"
  # The VPC where the targets are located
  vpc_id = var.vpc_id
  # Use IP target type because Fargate tasks use awsvpc networking
  # (each task gets its own ENI with a private IP)
  target_type = "ip"

  # Health check configuration - ALB uses this to determine if targets are healthy
  health_check {
    # Enable health checking
    enabled = true
    # Number of consecutive successful checks to mark a target as healthy
    healthy_threshold = 2
    # Number of consecutive failed checks to mark a target as unhealthy
    unhealthy_threshold = 3
    # Seconds to wait for a health check response before timing out
    timeout = 5
    # Seconds between health check requests
    interval = 30
    # URL path the ALB hits for health checks
    path = "/health"
    # Expected HTTP status code for a healthy response
    matcher = "200"
  }

  # Tags for resource identification
  tags = {
    Name = "${var.app_name}-tg"
  }

  # Create the new target group before destroying the old one
  # This prevents downtime during target group changes
  lifecycle {
    create_before_destroy = true
  }
}

# HTTP listener - redirects all HTTP traffic to HTTPS
# This ensures all communication is encrypted
resource "aws_lb_listener" "http" {
  # Attach this listener to our ALB
  load_balancer_arn = aws_lb.main.arn
  # Listen on port 80 (standard HTTP port)
  port = 80
  # Accept HTTP protocol
  protocol = "HTTP"

  # Redirect all HTTP requests to HTTPS with a 301 (permanent redirect)
  default_action {
    type = "redirect"
    redirect {
      # Redirect to port 443 (HTTPS)
      port = "443"
      # Use HTTPS protocol
      protocol = "HTTPS"
      # 301 = permanent redirect (browsers will cache this)
      status_code = "HTTP_301"
    }
  }
}

# HTTPS listener - handles all encrypted traffic and forwards to ECS targets
resource "aws_lb_listener" "https" {
  # Attach this listener to our ALB
  load_balancer_arn = aws_lb.main.arn
  # Listen on port 443 (standard HTTPS port)
  port = 443
  # Accept HTTPS protocol
  protocol = "HTTPS"
  # TLS security policy - uses TLS 1.3 with strong ciphers
  ssl_policy = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  # The ACM certificate ARN for SSL/TLS termination
  certificate_arn = var.certificate_arn

  # Forward traffic to the target group where ECS tasks are registered
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}
