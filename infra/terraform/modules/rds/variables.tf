# ============================================================================
# RDS Module - Input Variables
# These variables configure the PostgreSQL database and its secrets
# ============================================================================

# Application name used as prefix for all RDS resource names
variable "app_name" {
  description = "Application name used for resource naming"
  type        = string
}

# RDS instance class determines the compute and memory capacity
variable "db_instance_class" {
  description = "RDS instance class (e.g. db.t3.micro)"
  type        = string
}

# Storage size in gigabytes for the database
variable "db_allocated_storage" {
  description = "Allocated storage for RDS in GB"
  type        = number
}

# Name of the PostgreSQL database to create on launch
variable "db_name" {
  description = "Name of the database to create"
  type        = string
}

# Master username for database authentication
variable "db_username" {
  description = "Database master username"
  type        = string
  # Marked sensitive to prevent it from appearing in Terraform output/logs
  sensitive = true
}

# Private subnet IDs where the database is placed
variable "private_subnets" {
  description = "List of private subnet IDs for the DB subnet group"
  type        = list(string)
}

# Security group ID that controls access to the database
variable "rds_security_group_id" {
  description = "Security group ID for the RDS instance"
  type        = string
}

# Optional snapshot ID to restore from (null = create fresh database)
variable "db_snapshot_identifier" {
  description = "RDS snapshot identifier to restore from (null for fresh DB)"
  type        = string
  default     = null
}
