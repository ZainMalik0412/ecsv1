# ============================================================================
# RDS Module - Outputs
# These values are used by the ECS module for database connectivity
# ============================================================================

# Database endpoint in host:port format - used for connection configuration
output "endpoint" {
  description = "RDS instance endpoint (host:port)"
  value       = aws_db_instance.main.endpoint
  # Marked sensitive because it reveals the database hostname
  sensitive = true
}

# Database name - used in connection strings
output "db_name" {
  description = "Name of the database"
  value       = aws_db_instance.main.db_name
}

# ARN of the db-credentials secret - used in ECS task execution role policy
# to grant the container permission to read this secret
output "db_credentials_secret_arn" {
  description = "ARN of the database credentials secret"
  value       = aws_secretsmanager_secret.db_credentials.arn
}

# ARN of the database-url secret - injected into the container as DATABASE_URL
output "database_url_secret_arn" {
  description = "ARN of the database URL secret"
  value       = aws_secretsmanager_secret.database_url.arn
}
