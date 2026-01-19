variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "attendancems"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "zainecs.com"
}

variable "subdomain" {
  description = "Subdomain for the application"
  type        = string
  default     = "tm"
}

variable "container_port" {
  description = "Port exposed by the container"
  type        = number
  default     = 8080
}

variable "container_cpu" {
  description = "CPU units for the container"
  type        = number
  default     = 512
}

variable "container_memory" {
  description = "Memory for the container in MB"
  type        = number
  default     = 1024
}

variable "desired_count" {
  description = "Desired number of tasks"
  type        = number
  default     = 2
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "attendancems"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "attendancems"
  sensitive   = true
}

variable "github_org" {
  description = "GitHub organization or username"
  type        = string
  default     = "ZainMalik0412"
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
  default     = "ecsv1"
}
