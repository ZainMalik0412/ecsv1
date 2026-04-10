# ============================================================================
# VPC Module
# Creates the Virtual Private Cloud, subnets, NAT Gateway, and security groups
# that form the network foundation for all other AWS resources
# ============================================================================

# Use the official AWS VPC community module from the Terraform Registry
# This abstracts the complexity of creating route tables, IGW, NAT, etc.
module "vpc" {
  # Source from the Terraform Registry - maintained by HashiCorp and AWS
  source = "terraform-aws-modules/vpc/aws"
  # Pin to major version 5.x for stability while allowing patch updates
  version = "~> 5.0"

  # Name prefix applied to all VPC resources (subnets, route tables, etc.)
  name = "${var.app_name}-vpc"
  # CIDR block defines the IP range for the entire VPC - 65,536 addresses
  cidr = "10.0.0.0/16"

  # Deploy across 2 Availability Zones for high availability
  azs = ["${var.aws_region}a", "${var.aws_region}b"]
  # Private subnets for ECS tasks and RDS - not directly internet-accessible
  # Each /24 provides 256 IP addresses
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  # Public subnets for the ALB - directly reachable from the internet
  public_subnets = ["10.0.101.0/24", "10.0.102.0/24"]

  # NAT Gateway disabled to save ~$35/month
  # ECS tasks use public subnets with assign_public_ip instead
  # RDS remains in private subnets (no internet access needed)
  enable_nat_gateway = false
  single_nat_gateway = false
  # Enable DNS hostnames so EC2/ECS resources get DNS names within the VPC
  enable_dns_hostnames = true
  # Enable DNS resolution support for the VPC
  enable_dns_support = true

  # Tags applied to all resources created by this module
  tags = {
    Name = "${var.app_name}-vpc"
  }
}

# ============================================================================
# Security Group: Application Load Balancer
# Controls which traffic can reach the ALB from the public internet
# ============================================================================
resource "aws_security_group" "alb" {
  # Unique name for the security group within the VPC
  name = "${var.app_name}-alb-sg"
  # Human-readable description shown in the AWS console
  description = "Security group for ALB"
  # Associate this security group with our VPC
  vpc_id = module.vpc.vpc_id

  # Allow inbound HTTP traffic (port 80) from any IP address
  # Required so the ALB can redirect HTTP requests to HTTPS
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow inbound HTTPS traffic (port 443) from any IP address
  # This is the primary entry point for all application traffic
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow all outbound traffic so the ALB can forward requests to targets
  # and perform health checks against the ECS tasks
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Tags for resource identification and cost tracking
  tags = {
    Name = "${var.app_name}-alb-sg"
  }
}

# ============================================================================
# Security Group: ECS Tasks
# Controls traffic between the ALB and the application containers
# ============================================================================
resource "aws_security_group" "ecs" {
  # Unique name for the security group
  name = "${var.app_name}-ecs-sg"
  # Human-readable description
  description = "Security group for ECS tasks"
  # Associate with our VPC
  vpc_id = module.vpc.vpc_id

  # Only allow inbound traffic on the container port, and only from the ALB
  # This ensures containers are never directly accessible from the internet
  ingress {
    from_port       = var.container_port
    to_port         = var.container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # Allow all outbound traffic so containers can reach:
  # RDS database, ECR for image pulls, AWS APIs, and external services
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Tags for resource identification
  tags = {
    Name = "${var.app_name}-ecs-sg"
  }
}

# ============================================================================
# Security Group: RDS Database
# Controls traffic between ECS tasks and the PostgreSQL database
# ============================================================================
resource "aws_security_group" "rds" {
  # Unique name for the security group
  name = "${var.app_name}-rds-sg"
  # Human-readable description
  description = "Security group for RDS"
  # Associate with our VPC
  vpc_id = module.vpc.vpc_id

  # Only allow inbound PostgreSQL traffic (port 5432) from ECS tasks
  # This ensures the database is only accessible from application containers
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  # Allow all outbound traffic (needed for RDS maintenance and updates)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Tags for resource identification
  tags = {
    Name = "${var.app_name}-rds-sg"
  }
}

