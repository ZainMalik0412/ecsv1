# ============================================================================
# Bootstrap Configuration
# This is a ONE-TIME setup that creates the S3 bucket and DynamoDB table
# needed for Terraform remote state storage and state locking.
# Run this BEFORE the main Terraform configuration.
# ============================================================================

terraform {
  # Minimum Terraform version required
  required_version = ">= 1.5.0"

  # Declare required providers
  required_providers {
    # AWS provider for creating S3, DynamoDB, IAM, and OIDC resources
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Configure the AWS provider with region and default tags
provider "aws" {
  # AWS region where bootstrap resources are created
  region = var.aws_region

  # Default tags applied to all resources created by this configuration
  default_tags {
    tags = {
      # Project name for cost allocation
      Project = "AttendanceMS"
      # Indicates resources are managed by Terraform
      ManagedBy = "Terraform"
      # Identifies these as state backend resources
      Purpose = "State Backend"
    }
  }
}

# ---- Input Variables ----

# AWS region for all bootstrap resources
variable "aws_region" {
  description = "AWS region for bootstrap resources"
  type        = string
  default     = "eu-west-2"
}

# Application name used as prefix for resource naming
variable "app_name" {
  description = "Application name for resource naming"
  type        = string
  default     = "attendancems"
}

# ============================================================================
# S3 Bucket for Terraform State
# Stores the terraform.tfstate file remotely so multiple team members
# can collaborate and state is not lost if a local machine fails
# ============================================================================
resource "aws_s3_bucket" "terraform_state" {
  # Bucket name must be globally unique across all AWS accounts
  bucket = "${var.app_name}-terraform-state"

  # Prevent accidental deletion of this bucket (contains critical state data)
  lifecycle {
    prevent_destroy = true
  }

  # Tags for identification
  tags = {
    Name = "${var.app_name}-terraform-state"
  }
}

# Enable versioning on the state bucket so previous state versions are preserved
# This allows recovery if the state file is accidentally corrupted or deleted
resource "aws_s3_bucket_versioning" "terraform_state" {
  # Apply to our state bucket
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    # Enable versioning to keep history of all state file changes
    status = "Enabled"
  }
}

# Enable server-side encryption for the state bucket
# State files contain sensitive information (passwords, ARNs, etc.)
resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  # Apply to our state bucket
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      # AES256 encryption using AWS-managed keys (free, no KMS costs)
      sse_algorithm = "AES256"
    }
  }
}

# Block all public access to the state bucket
# State files must NEVER be publicly accessible
resource "aws_s3_bucket_public_access_block" "terraform_state" {
  # Apply to our state bucket
  bucket = aws_s3_bucket.terraform_state.id

  # Block new public ACLs from being applied
  block_public_acls = true
  # Block new public bucket policies from being applied
  block_public_policy = true
  # Ignore any existing public ACLs on objects
  ignore_public_acls = true
  # Restrict access to bucket owner only
  restrict_public_buckets = true
}

# ============================================================================
# DynamoDB Table for State Locking
# Prevents concurrent Terraform operations from corrupting the state file
# When one user runs terraform apply, others are blocked until it completes
# ============================================================================
resource "aws_dynamodb_table" "terraform_locks" {
  # Table name referenced in the main Terraform backend configuration
  name = "${var.app_name}-terraform-locks"
  # Pay-per-request billing avoids provisioned capacity costs
  # Ideal for low-traffic use (only accessed during terraform operations)
  billing_mode = "PAY_PER_REQUEST"
  # Primary key used by Terraform to create and check lock entries
  hash_key = "LockID"

  # Define the primary key attribute (string type)
  attribute {
    name = "LockID"
    type = "S"
  }

  # Tags for identification
  tags = {
    Name = "${var.app_name}-terraform-locks"
  }
}

# ---- Bootstrap Outputs ----

# S3 bucket name - use this value in the main Terraform backend config
output "s3_bucket_name" {
  description = "S3 bucket name for Terraform remote state storage"
  value       = aws_s3_bucket.terraform_state.id
}

# DynamoDB table name - use this value in the main Terraform backend config
output "dynamodb_table_name" {
  description = "DynamoDB table name for Terraform state locking"
  value       = aws_dynamodb_table.terraform_locks.name
}

# =============================================================================
# GitHub OIDC Provider
# Enables GitHub Actions to authenticate with AWS using short-lived tokens
# instead of storing long-lived AWS access keys as GitHub secrets
# This is the recommended approach for CI/CD security
# =============================================================================
resource "aws_iam_openid_connect_provider" "github" {
  # GitHub's OIDC token issuer URL
  url = "https://token.actions.githubusercontent.com"
  # The audience claim that must be present in the OIDC token
  client_id_list = ["sts.amazonaws.com"]
  # TLS certificate thumbprints for the OIDC provider (GitHub's certificates)
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1", "1c58a3a8518e8759bf075b76b750d4f2df264fcd"]

  # Tags for identification
  tags = {
    Name = "${var.app_name}-github-oidc"
  }
}

# =============================================================================
# GitHub Actions IAM Role
# This role is assumed by GitHub Actions workflows via OIDC federation
# It grants all permissions needed to create, manage, and destroy infrastructure
# =============================================================================

# GitHub organisation or username that owns the repository
variable "github_org" {
  description = "GitHub organisation/username for OIDC trust policy"
  type        = string
  default     = "ZainMalik0412"
}

# GitHub repository name - only this repo can assume the role
variable "github_repo" {
  description = "GitHub repository name for OIDC trust policy"
  type        = string
  default     = "ecsv1"
}

# Fetch current AWS account ID for constructing scoped ARNs in policies
data "aws_caller_identity" "current" {}

# IAM role that GitHub Actions assumes via OIDC
resource "aws_iam_role" "github_actions" {
  # Role name visible in the AWS console
  name = "${var.app_name}-github-actions-role"
  # Maximum session duration in seconds (1 hour - enough for most deployments)
  max_session_duration = 3600

  # Trust policy: defines WHO can assume this role
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          # Trust the GitHub OIDC provider we created above
          Federated = aws_iam_openid_connect_provider.github.arn
        }
        # Allow web identity federation (OIDC token exchange for AWS credentials)
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            # Verify the token audience matches STS
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            # Only allow tokens from this specific GitHub repo (any branch/ref)
            "token.actions.githubusercontent.com:sub" = "repo:${var.github_org}/${var.github_repo}:*"
          }
        }
      }
    ]
  })

  # Tags for identification
  tags = {
    Name = "${var.app_name}-github-actions-role"
  }
}

# =============================================================================
# IAM Policy: Terraform State Access
# Grants read/write access to the S3 state bucket and DynamoDB lock table
# This is always required for any Terraform operation (plan, apply, destroy)
# =============================================================================
resource "aws_iam_role_policy" "github_actions_terraform_state" {
  # Policy name for identification
  name = "${var.app_name}-github-actions-terraform-state-policy"
  # Attach to the GitHub Actions role
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # S3 permissions for reading and writing the state file
        Sid    = "S3StateAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",    # Read the current state file
          "s3:PutObject",    # Write updated state after apply
          "s3:DeleteObject", # Delete state during destroy cleanup
          "s3:ListBucket"    # List bucket contents for state discovery
        ]
        Resource = [
          # The bucket itself (for ListBucket)
          aws_s3_bucket.terraform_state.arn,
          # All objects in the bucket (for Get/Put/Delete)
          "${aws_s3_bucket.terraform_state.arn}/*"
        ]
      },
      {
        # DynamoDB permissions for state locking
        Sid    = "DynamoDBLockAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",   # Check if state is locked
          "dynamodb:PutItem",   # Acquire a lock before operations
          "dynamodb:DeleteItem" # Release the lock after operations
        ]
        # Scoped to only the locks table
        Resource = aws_dynamodb_table.terraform_locks.arn
      }
    ]
  })
}

# =============================================================================
# IAM Policy: Full Infrastructure Management
# Grants all permissions needed by Terraform to create, update, and destroy
# the complete application infrastructure (VPC, ECS, ALB, RDS, etc.)
# Organised by AWS service for clarity
# =============================================================================
resource "aws_iam_role_policy" "github_actions_terraform_infra" {
  # Policy name for identification
  name = "${var.app_name}-github-actions-terraform-infra-policy"
  # Attach to the GitHub Actions role
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # Read-only access across all services for terraform plan and refresh
        # These Describe/List actions let Terraform check current resource state
        Sid    = "TerraformReadAccess"
        Effect = "Allow"
        Action = [
          "ec2:Describe*",                    # VPC, subnets, security groups, NAT, EIPs
          "elasticloadbalancing:Describe*",   # ALB, target groups, listeners
          "rds:Describe*",                    # DB instances, snapshots, subnet groups
          "rds:ListTagsForResource",          # Read tags on RDS resources
          "secretsmanager:Describe*",         # Secret metadata
          "secretsmanager:GetSecretValue",    # Read secret values (for state)
          "secretsmanager:GetResourcePolicy", # Read secret resource policies
          "secretsmanager:ListSecrets",       # List all secrets
          "logs:Describe*",                   # CloudWatch log group details
          "logs:List*",                       # List log groups and streams
          "acm:Describe*",                    # Certificate details and status
          "acm:List*",                        # List certificates
          "route53:Get*",                     # Hosted zone and record details
          "route53:List*",                    # List zones and records
          "iam:Get*",                         # Role and policy details
          "iam:List*",                        # List roles and policies
          "ecr:Describe*",                    # Repository details
          "ecr:List*",                        # List repositories and images
          "ecr:GetLifecyclePolicy",           # Read lifecycle policy config
          "ecs:Describe*",                    # Cluster, service, task details
          "ecs:List*"                         # List clusters, services, tasks
        ]
        Resource = "*"
      },
      {
        # VPC and networking permissions
        # Covers VPC, subnets, route tables, gateways, security groups, etc.
        Sid    = "TerraformVPCAccess"
        Effect = "Allow"
        Action = [
          "ec2:CreateVpc",                     # Create the VPC
          "ec2:DeleteVpc",                     # Delete the VPC on destroy
          "ec2:ModifyVpcAttribute",            # Enable DNS hostnames/support
          "ec2:CreateSubnet",                  # Create public and private subnets
          "ec2:DeleteSubnet",                  # Delete subnets on destroy
          "ec2:CreateRouteTable",              # Create route tables for subnets
          "ec2:DeleteRouteTable",              # Delete route tables on destroy
          "ec2:CreateRoute",                   # Add routes (e.g. to NAT/IGW)
          "ec2:DeleteRoute",                   # Remove routes on destroy
          "ec2:AssociateRouteTable",           # Associate route tables with subnets
          "ec2:DisassociateRouteTable",        # Disassociate on destroy
          "ec2:CreateInternetGateway",         # Create IGW for public internet access
          "ec2:DeleteInternetGateway",         # Delete IGW on destroy
          "ec2:AttachInternetGateway",         # Attach IGW to VPC
          "ec2:DetachInternetGateway",         # Detach IGW on destroy
          "ec2:CreateNatGateway",              # Create NAT for private subnet internet
          "ec2:DeleteNatGateway",              # Delete NAT on destroy
          "ec2:AllocateAddress",               # Allocate Elastic IP for NAT Gateway
          "ec2:ReleaseAddress",                # Release Elastic IP on destroy
          "ec2:AssociateAddress",              # Associate EIP with NAT
          "ec2:DisassociateAddress",           # Disassociate EIP on destroy
          "ec2:CreateSecurityGroup",           # Create SGs for ALB, ECS, RDS
          "ec2:DeleteSecurityGroup",           # Delete SGs on destroy
          "ec2:AuthorizeSecurityGroupIngress", # Add inbound rules
          "ec2:AuthorizeSecurityGroupEgress",  # Add outbound rules
          "ec2:RevokeSecurityGroupIngress",    # Remove inbound rules
          "ec2:RevokeSecurityGroupEgress",     # Remove outbound rules
          "ec2:CreateTags",                    # Tag EC2 resources
          "ec2:DeleteTags",                    # Remove tags on destroy
          "ec2:CreateNetworkInterface",        # Create ENIs (used by Fargate)
          "ec2:DeleteNetworkInterface",        # Delete ENIs on destroy
          "ec2:DetachNetworkInterface",        # Detach ENIs before deletion
          "ec2:CreateNetworkAcl",              # Create network ACLs
          "ec2:DeleteNetworkAcl",              # Delete ACLs on destroy
          "ec2:CreateNetworkAclEntry",         # Add ACL rules
          "ec2:DeleteNetworkAclEntry",         # Remove ACL rules
          "ec2:ReplaceNetworkAclEntry",        # Update ACL rules
          "ec2:ReplaceNetworkAclAssociation"   # Change ACL subnet associations
        ]
        Resource = "*"
      },
      {
        # Application Load Balancer permissions
        # Covers ALB, target groups, listeners, and listener rules
        Sid    = "TerraformALBAccess"
        Effect = "Allow"
        Action = [
          "elasticloadbalancing:Create*",     # Create ALB, TG, listeners
          "elasticloadbalancing:Delete*",     # Delete ALB resources on destroy
          "elasticloadbalancing:Modify*",     # Modify ALB attributes
          "elasticloadbalancing:Register*",   # Register targets in target groups
          "elasticloadbalancing:Deregister*", # Deregister targets
          "elasticloadbalancing:Set*",        # Set ALB attributes
          "elasticloadbalancing:AddTags",     # Tag ALB resources
          "elasticloadbalancing:RemoveTags"   # Remove tags on destroy
        ]
        Resource = "*"
      },
      {
        # RDS database permissions
        # Covers DB instances, subnet groups, snapshots, and tags
        Sid    = "TerraformRDSAccess"
        Effect = "Allow"
        Action = [
          "rds:CreateDBInstance",                # Create the PostgreSQL database
          "rds:DeleteDBInstance",                # Delete the database on destroy
          "rds:ModifyDBInstance",                # Modify DB settings
          "rds:CreateDBSubnetGroup",             # Create DB subnet group
          "rds:DeleteDBSubnetGroup",             # Delete subnet group on destroy
          "rds:ModifyDBSubnetGroup",             # Modify subnet group membership
          "rds:AddTagsToResource",               # Tag RDS resources
          "rds:RemoveTagsFromResource",          # Remove tags on destroy
          "rds:CreateDBSnapshot",                # Create snapshots before destroy
          "rds:DeleteDBSnapshot",                # Clean up old snapshots
          "rds:RestoreDBInstanceFromDBSnapshot", # Restore from snapshot on rebuild
          "rds:DescribeDBSnapshots"              # List available snapshots
        ]
        Resource = "*"
      },
      {
        # SSM Parameter Store permissions
        # Used to store the latest RDS snapshot ID for rebuild
        Sid    = "SSMParameterAccess"
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",   # Read the snapshot ID parameter
          "ssm:PutParameter",   # Store the snapshot ID after destroy
          "ssm:DeleteParameter" # Clean up parameters
        ]
        # Scoped to only parameters under the app namespace
        Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/attendancems/*"
      },
      {
        # Secrets Manager permissions
        # Used to create secrets for DB credentials, DATABASE_URL, and JWT
        Sid    = "TerraformSecretsAccess"
        Effect = "Allow"
        Action = [
          "secretsmanager:CreateSecret",   # Create new secrets
          "secretsmanager:DeleteSecret",   # Delete secrets on destroy
          "secretsmanager:UpdateSecret",   # Update secret metadata
          "secretsmanager:PutSecretValue", # Store secret values
          "secretsmanager:TagResource",    # Tag secrets
          "secretsmanager:UntagResource"   # Remove tags on destroy
        ]
        # Scoped to only secrets under the app namespace
        Resource = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.app_name}/*"
      },
      {
        # ECS permissions
        # Covers clusters, services, task definitions, and capacity providers
        Sid    = "TerraformECSAccess"
        Effect = "Allow"
        Action = [
          "ecs:CreateCluster",               # Create the ECS cluster
          "ecs:DeleteCluster",               # Delete cluster on destroy
          "ecs:CreateService",               # Create the Fargate service
          "ecs:DeleteService",               # Delete service on destroy
          "ecs:UpdateService",               # Update service (new task def, count)
          "ecs:UpdateCluster",               # Update cluster settings
          "ecs:PutClusterCapacityProviders", # Configure Fargate/Spot providers
          "ecs:TagResource",                 # Tag ECS resources
          "ecs:UntagResource",               # Remove tags on destroy
          "ecs:RegisterTaskDefinition",      # Register new task definitions
          "ecs:DeregisterTaskDefinition"     # Deregister old task definitions
        ]
        Resource = "*"
      },
      {
        # CloudWatch Logs permissions
        # Used to create and manage log groups for ECS container output
        Sid    = "TerraformLogsAccess"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",     # Create log group for ECS
          "logs:DeleteLogGroup",     # Delete log group on destroy
          "logs:DescribeLogGroups",  # Check log group state
          "logs:PutRetentionPolicy", # Set log retention period (7 days)
          "logs:TagResource",        # Tag log groups
          "logs:UntagResource"       # Remove tags on destroy
        ]
        Resource = "*"
      },
      {
        # ACM (Certificate Manager) permissions
        # Used to request and manage SSL/TLS certificates for HTTPS
        Sid    = "TerraformACMAccess"
        Effect = "Allow"
        Action = [
          "acm:RequestCertificate",        # Request a new SSL certificate
          "acm:DeleteCertificate",         # Delete certificate on destroy
          "acm:AddTagsToCertificate",      # Tag certificates
          "acm:RemoveTagsFromCertificate", # Remove tags on destroy
          "acm:GetCertificate"             # Retrieve certificate details
        ]
        Resource = "*"
      },
      {
        # Route 53 DNS permissions
        # Used to create DNS records for domain and certificate validation
        Sid    = "TerraformRoute53Access"
        Effect = "Allow"
        Action = [
          "route53:ChangeResourceRecordSets", # Create/update/delete DNS records
          "route53:GetChange",                # Check if DNS changes have propagated
          "route53:ListHostedZones",          # Find the hosted zone
          "route53:ListHostedZonesByName",    # Look up zone by domain name
          "route53:ListResourceRecordSets"    # List existing DNS records
        ]
        Resource = [
          # Allow operations on any hosted zone
          "arn:aws:route53:::hostedzone/*",
          # Allow checking change propagation status
          "arn:aws:route53:::change/*"
        ]
      },
      {
        # IAM permissions
        # Used to create ECS task execution and task roles
        Sid    = "TerraformIAMAccess"
        Effect = "Allow"
        Action = [
          "iam:CreateRole",             # Create ECS task roles
          "iam:DeleteRole",             # Delete roles on destroy
          "iam:AttachRolePolicy",       # Attach AWS-managed policies
          "iam:DetachRolePolicy",       # Detach policies on destroy
          "iam:PutRolePolicy",          # Create inline policies
          "iam:DeleteRolePolicy",       # Delete inline policies on destroy
          "iam:TagRole",                # Tag IAM roles
          "iam:UntagRole",              # Remove tags on destroy
          "iam:UpdateAssumeRolePolicy", # Update role trust policies
          "iam:PassRole"                # Allow ECS to use the roles
        ]
        Resource = "*"
      },
      {
        # ECR (Container Registry) permissions
        # Covers repository management and Docker image push/pull
        Sid    = "TerraformECRAccess"
        Effect = "Allow"
        Action = [
          "ecr:CreateRepository",              # Create the ECR repository
          "ecr:DeleteRepository",              # Delete repository on destroy
          "ecr:PutLifecyclePolicy",            # Set image cleanup policy
          "ecr:DeleteLifecyclePolicy",         # Remove lifecycle policy
          "ecr:TagResource",                   # Tag the repository
          "ecr:UntagResource",                 # Remove tags on destroy
          "ecr:PutImageScanningConfiguration", # Configure vulnerability scanning
          "ecr:GetAuthorizationToken",         # Authenticate Docker client
          "ecr:BatchCheckLayerAvailability",   # Check if image layers exist
          "ecr:GetDownloadUrlForLayer",        # Download image layers
          "ecr:BatchGetImage",                 # Pull image manifests
          "ecr:BatchDeleteImage",              # Delete old images
          "ecr:ListImages",                    # List images in repository
          "ecr:PutImage",                      # Push new image tags
          "ecr:InitiateLayerUpload",           # Start uploading image layers
          "ecr:UploadLayerPart",               # Upload image layer chunks
          "ecr:CompleteLayerUpload"            # Finish layer upload
        ]
        Resource = "*"
      }
    ]
  })
}

# ---- OIDC / IAM Outputs ----

# Role ARN - add this as the AWS_ROLE_ARN secret in GitHub repository settings
output "github_actions_role_arn" {
  description = "ARN of the GitHub Actions IAM role (add as AWS_ROLE_ARN secret)"
  value       = aws_iam_role.github_actions.arn
}

# OIDC provider ARN - for reference and debugging
output "github_oidc_provider_arn" {
  description = "ARN of the GitHub OIDC provider"
  value       = aws_iam_openid_connect_provider.github.arn
}
