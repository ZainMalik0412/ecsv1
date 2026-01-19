# AttendanceMS - Production Deployment Guide

This guide walks you through deploying AttendanceMS to AWS using Terraform and GitHub Actions.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS Cloud (eu-west-2)                          │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                              VPC (10.0.0.0/16)                        │  │
│  │  ┌─────────────────────────┐    ┌─────────────────────────────────┐  │  │
│  │  │    Public Subnets       │    │       Private Subnets           │  │  │
│  │  │  ┌─────────────────┐    │    │  ┌─────────────────────────┐    │  │  │
│  │  │  │      ALB        │────│────│──│   ECS Fargate Tasks     │    │  │  │
│  │  │  │  (HTTPS/443)    │    │    │  │   (attendancems)        │    │  │  │
│  │  │  └─────────────────┘    │    │  └───────────┬─────────────┘    │  │  │
│  │  │          │              │    │              │                  │  │  │
│  │  │  ┌───────┴───────┐      │    │  ┌───────────▼─────────────┐    │  │  │
│  │  │  │  NAT Gateway  │──────│────│──│    RDS PostgreSQL       │    │  │  │
│  │  │  └───────────────┘      │    │  │    (db.t3.micro)        │    │  │  │
│  │  └─────────────────────────┘    │  └─────────────────────────┘    │  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐│
│  │     ECR     │  │     ACM     │  │  Route 53   │  │  Secrets Manager    ││
│  │ (Container) │  │   (HTTPS)   │  │   (DNS)     │  │ (DB creds, JWT)     ││
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **Route 53 Hosted Zone** for your domain (e.g., `zainecs.com`)
3. **Terraform** >= 1.5.0 installed locally
4. **AWS CLI** configured with credentials
5. **GitHub Repository** with Actions enabled

---

## Step 1: Bootstrap Terraform State Backend (ONE-TIME)

Before running the main Terraform, you need to create the S3 bucket and DynamoDB table for state management.

```bash
cd infra/terraform/bootstrap

# Initialize and apply
terraform init
terraform apply
```

This creates:
- S3 bucket: `attendancems-terraform-state`
- DynamoDB table: `attendancems-terraform-locks`

---

## Step 2: Configure Terraform Variables

```bash
cd infra/terraform

# Copy example variables
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
nano terraform.tfvars
```

**Required variables:**
```hcl
aws_region   = "eu-west-2"
environment  = "prod"
app_name     = "attendancems"
domain_name  = "yourdomain.com"      # Your Route 53 domain
subdomain    = "tm"                   # Creates tm.yourdomain.com

# GitHub OIDC (for CI/CD)
github_org  = "your-github-username"
github_repo = "your-repo-name"
```

---

## Step 3: Deploy Infrastructure

```bash
cd infra/terraform

# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Apply infrastructure
terraform apply
```

**What gets created:**
- VPC with public/private subnets across 2 AZs
- NAT Gateway for outbound internet access
- Application Load Balancer with HTTPS
- ACM certificate (auto-validated via DNS)
- ECS Fargate cluster and service
- RDS PostgreSQL 16 database
- ECR repository for Docker images
- Security groups (ALB → ECS → RDS)
- Secrets Manager secrets (DB credentials, JWT secret)
- IAM roles for ECS tasks and GitHub Actions OIDC

---

## Step 4: Build and Push Initial Docker Image

After Terraform creates the ECR repository, push your first image:

```bash
# Get ECR repository URL from Terraform output
ECR_URL=$(terraform output -raw ecr_repository_url)

# Login to ECR
aws ecr get-login-password --region eu-west-2 | docker login --username AWS --password-stdin $ECR_URL

# Build and push
docker build -t $ECR_URL:latest .
docker push $ECR_URL:latest
```

---

## Step 5: Configure GitHub Actions

### 5.1 Get the IAM Role ARN

```bash
cd infra/terraform
terraform output github_actions_role_arn
```

### 5.2 Add GitHub Secret

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `AWS_ROLE_ARN`
5. Value: The ARN from step 5.1

### 5.3 Create GitHub Environment (Optional but recommended)

1. Go to **Settings** → **Environments**
2. Click **New environment**
3. Name: `production`
4. Add protection rules (require reviewers, etc.)

---

## Step 6: Trigger First Deployment

Push to main branch to trigger the CI/CD pipeline:

```bash
git add .
git commit -m "Initial deployment"
git push origin main
```

The pipeline will:
1. Run tests
2. Build Docker image tagged with commit SHA
3. Push to ECR
4. Apply any Terraform changes
5. Deploy to ECS
6. Run health checks

---

## Outputs

After deployment, access these outputs:

```bash
cd infra/terraform

# Application URL
terraform output app_url
# https://tm.zainecs.com

# ALB DNS name (for debugging)
terraform output alb_dns_name

# ECR repository URL
terraform output ecr_repository_url

# ECS cluster and service names
terraform output ecs_cluster_name
terraform output ecs_service_name
```

---

## Manual Steps Summary

| Step | Action | One-Time? |
|------|--------|-----------|
| 1 | Run bootstrap Terraform for S3/DynamoDB | ✅ Yes |
| 2 | Create `terraform.tfvars` from example | ✅ Yes |
| 3 | Run `terraform apply` for main infrastructure | ✅ Yes |
| 4 | Build and push initial Docker image | ✅ Yes |
| 5 | Add `AWS_ROLE_ARN` secret to GitHub | ✅ Yes |
| 6 | Create GitHub environment (optional) | ✅ Yes |

After these steps, all future deployments are automated via GitHub Actions.

---

## Troubleshooting

### ECS Tasks Not Starting

Check CloudWatch logs:
```bash
aws logs tail /ecs/attendancems --follow
```

### Database Connection Issues

Verify security group allows ECS → RDS on port 5432:
```bash
aws ec2 describe-security-groups --group-ids <ecs-sg-id> <rds-sg-id>
```

### ACM Certificate Pending

Certificate validation can take up to 30 minutes. Check status:
```bash
aws acm describe-certificate --certificate-arn <cert-arn>
```

### GitHub Actions OIDC Failing

Verify the role trust policy allows your specific repo:
```bash
aws iam get-role --role-name attendancems-github-actions-role --query 'Role.AssumeRolePolicyDocument'
```

---

## Cost Estimation

| Resource | Monthly Cost (USD) |
|----------|-------------------|
| ECS Fargate (2 tasks, 0.5 vCPU, 1GB) | ~$30 |
| RDS PostgreSQL (db.t3.micro) | ~$15 |
| NAT Gateway | ~$35 |
| ALB | ~$20 |
| Route 53 | ~$0.50 |
| ECR Storage | ~$1 |
| **Total** | **~$100/month** |

To reduce costs:
- Use 1 task instead of 2 (`desired_count = 1`)
- Use `db.t3.micro` (already configured)
- Consider removing NAT Gateway if outbound internet not needed

---

## Security Considerations

1. **HTTPS Only** - ALB redirects HTTP to HTTPS
2. **Private Subnets** - ECS and RDS are not publicly accessible
3. **Secrets Manager** - Database credentials and JWT secret stored securely
4. **OIDC** - No long-lived AWS credentials in GitHub
5. **Security Groups** - Minimal access (ALB→ECS→RDS only)
6. **Encryption** - RDS storage encrypted, S3 state bucket encrypted

---

## Cleanup

To destroy all resources:

```bash
cd infra/terraform

# Destroy main infrastructure
terraform destroy

# Destroy bootstrap resources (optional)
cd bootstrap
terraform destroy
```

⚠️ **Warning**: This will delete all data including the RDS database!
