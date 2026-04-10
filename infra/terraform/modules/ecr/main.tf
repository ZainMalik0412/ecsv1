# ============================================================================
# ECR Module
# Creates an Elastic Container Registry repository to store Docker images
# pushed by the CI/CD pipeline and pulled by ECS tasks
# ============================================================================

# ECR repository to store the application's Docker images
resource "aws_ecr_repository" "app" {
  # Repository name - used in docker push/pull commands
  name = var.app_name
  # MUTABLE allows overwriting tags (e.g. "latest") - needed for CI/CD
  image_tag_mutability = "MUTABLE"
  # Allow Terraform to delete the repo even if it contains images
  force_delete = true

  # Automatically scan images for known vulnerabilities when pushed
  image_scanning_configuration {
    scan_on_push = true
  }

  # Tags for resource identification
  tags = {
    Name = var.app_name
  }
}

# Lifecycle policy to automatically clean up old images and control storage costs
resource "aws_ecr_lifecycle_policy" "app" {
  # Attach this policy to our ECR repository
  repository = aws_ecr_repository.app.name

  # Policy rules defined as JSON - ECR requires this format
  policy = jsonencode({
    rules = [
      {
        # Priority determines rule evaluation order (lower = higher priority)
        rulePriority = 1
        # Human-readable description of what this rule does
        description = "Keep last 3 images"
        selection = {
          # Apply to all images regardless of tag status
          tagStatus = "any"
          # Trigger when image count exceeds the threshold
          countType = "imageCountMoreThan"
          # Keep only the 3 most recent images to minimise storage costs
          countNumber = 3
        }
        action = {
          # Remove images that match the selection criteria
          type = "expire"
        }
      }
    ]
  })
}
