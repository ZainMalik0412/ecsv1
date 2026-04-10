# ============================================================================
# Terraform Configuration
# Defines the backend for state storage, required providers, and module calls
# This is the root module that orchestrates all infrastructure components
# ============================================================================

terraform {
  # Minimum Terraform version required to use this configuration
  required_version = ">= 1.5.0"

  # Declare required providers and their version constraints
  required_providers {
    # AWS provider for creating all cloud resources
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    # Random provider for generating passwords and secrets
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }

  # S3 backend stores Terraform state remotely for team collaboration
  # State locking via DynamoDB prevents concurrent modifications
  backend "s3" {
    # S3 bucket name where the state file is stored
    bucket = "attendancems-terraform-state"
    # Path within the bucket for the state file
    key = "prod/terraform.tfstate"
    # Region where the S3 bucket is located
    region = "eu-west-2"
    # Encrypt the state file at rest using server-side encryption
    encrypt = true
    # DynamoDB table used for state locking to prevent concurrent writes
    dynamodb_table = "attendancems-terraform-locks"
  }
}

# Fetch the current AWS account ID (used for constructing ARNs)
data "aws_caller_identity" "current" {}
# Fetch the current AWS region (used in resource configurations)
data "aws_region" "current" {}

# ============================================================================
# Module: VPC
# Creates the network foundation: VPC, subnets, NAT Gateway, security groups
# ============================================================================
module "vpc" {
  # Path to the local VPC module
  source = "./modules/vpc"

  # Pass required variables to the VPC module
  app_name       = var.app_name
  aws_region     = var.aws_region
  container_port = var.container_port
}

# ============================================================================
# Module: ECR
# Creates the container registry for storing Docker images
# ============================================================================
module "ecr" {
  # Path to the local ECR module
  source = "./modules/ecr"

  # Pass the application name for repository naming
  app_name = var.app_name
}

# ============================================================================
# Module: ACM
# Creates/looks up the SSL certificate and DNS records for HTTPS
# Depends on ALB module for the DNS alias record
# ============================================================================
module "acm" {
  # Path to the local ACM module
  source = "./modules/acm"

  # Domain and naming configuration
  domain_name = var.domain_name
  subdomain   = var.subdomain
  app_name    = var.app_name
  # ALB details needed for the Route 53 alias record
  alb_dns_name = module.alb.dns_name
  alb_zone_id  = module.alb.zone_id
}

# ============================================================================
# Module: ALB
# Creates the Application Load Balancer with HTTP->HTTPS redirect
# ============================================================================
module "alb" {
  # Path to the local ALB module
  source = "./modules/alb"

  # Application name and networking configuration
  app_name              = var.app_name
  vpc_id                = module.vpc.vpc_id
  public_subnets        = module.vpc.public_subnets
  alb_security_group_id = module.vpc.alb_security_group_id
  container_port        = var.container_port
  # SSL certificate for HTTPS listener
  certificate_arn = module.acm.certificate_arn
}

# ============================================================================
# Module: RDS
# Creates the PostgreSQL database and stores credentials in Secrets Manager
# ============================================================================
module "rds" {
  # Path to the local RDS module
  source = "./modules/rds"

  # Database configuration
  app_name             = var.app_name
  db_instance_class    = var.db_instance_class
  db_allocated_storage = var.db_allocated_storage
  db_name              = var.db_name
  db_username          = var.db_username
  # Network placement in private subnets with RDS security group
  private_subnets       = module.vpc.private_subnets
  rds_security_group_id = module.vpc.rds_security_group_id
  # Optional snapshot ID for restoring data after a destroy/rebuild cycle
  db_snapshot_identifier = var.db_snapshot_identifier
}

# ============================================================================
# Module: ECS
# Creates the Fargate cluster, service, task definition, and IAM roles
# This is where the application container actually runs
# ============================================================================
module "ecs" {
  # Path to the local ECS module
  source = "./modules/ecs"

  # Application and environment configuration
  app_name    = var.app_name
  environment = var.environment
  aws_region  = var.aws_region
  # Container resource allocation
  container_port   = var.container_port
  container_cpu    = var.container_cpu
  container_memory = var.container_memory
  desired_count    = var.desired_count
  # Network placement in public subnets (NAT Gateway removed for cost savings)
  # Security maintained via security groups (ECS SG only allows ALB inbound)
  ecs_subnets           = module.vpc.public_subnets
  ecs_security_group_id = module.vpc.ecs_security_group_id
  # ECR repository URL for pulling the Docker image
  ecr_repository_url = module.ecr.repository_url
  # ALB integration for load balancing and health checks
  target_group_arn   = module.alb.target_group_arn
  https_listener_arn = module.alb.https_listener_arn
  # Secrets Manager ARNs for the ECS task execution role policy
  db_credentials_secret_arn = module.rds.db_credentials_secret_arn
  database_url_secret_arn   = module.rds.database_url_secret_arn
}
