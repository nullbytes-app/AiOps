# ============================================================================
# Terraform Variables for Production Kubernetes Cluster
# ============================================================================
#
# This file defines all input variables for cluster provisioning.
# See terraform.tfvars.example for example configurations.
#

# ============================================================================
# Cloud Provider Configuration
# ============================================================================

variable "aws_region" {
  description = "AWS region for cluster deployment (e.g., us-east-1, eu-west-1)"
  type        = string
  default     = "us-east-1"

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-\\d{1}$", var.aws_region))
    error_message = "AWS region must be valid format (e.g., us-east-1, eu-west-1)"
  }
}

# ============================================================================
# Cluster Configuration (AC1, AC2)
# ============================================================================

variable "cluster_name" {
  description = "Name of the Kubernetes cluster (used for all resources)"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.cluster_name)) && length(var.cluster_name) <= 63
    error_message = "Cluster name must be alphanumeric with hyphens, max 63 characters"
  }
}

variable "kubernetes_version" {
  description = "Kubernetes version (e.g., 1.28, 1.29)"
  type        = string
  default     = "1.29"

  validation {
    condition     = can(regex("^1\\.[0-9]{2}$", var.kubernetes_version))
    error_message = "Kubernetes version must be in format 1.XX (e.g., 1.28, 1.29)"
  }
}

variable "vpc_cidr_block" {
  description = "CIDR block for VPC (must be large enough for all subnets)"
  type        = string
  default     = "10.0.0.0/16"

  validation {
    condition     = can(cidrhost(var.vpc_cidr_block, 0))
    error_message = "VPC CIDR must be valid CIDR notation"
  }
}

# ============================================================================
# Node Configuration (AC2: HA with 3+ nodes)
# ============================================================================

variable "min_node_count" {
  description = "Minimum number of worker nodes (auto-scaling minimum)"
  type        = number
  default     = 3

  validation {
    condition     = var.min_node_count >= 1 && var.min_node_count <= 10
    error_message = "Min nodes must be between 1 and 10"
  }
}

variable "max_node_count" {
  description = "Maximum number of worker nodes (auto-scaling maximum)"
  type        = number
  default     = 10

  validation {
    condition     = var.max_node_count >= var.min_node_count && var.max_node_count <= 100
    error_message = "Max nodes must be >= min nodes and <= 100"
  }
}

variable "desired_node_count" {
  description = "Desired number of worker nodes at startup"
  type        = number
  default     = 3

  validation {
    condition     = var.desired_node_count >= var.min_node_count && var.desired_node_count <= var.max_node_count
    error_message = "Desired nodes must be between min and max"
  }
}

variable "node_instance_types" {
  description = "EC2 instance types for worker nodes (e.g., [\"t3.large\", \"t3.xlarge\"])"
  type        = list(string)
  default     = ["t3.large"]

  validation {
    condition     = length(var.node_instance_types) > 0
    error_message = "At least one instance type must be specified"
  }
}

# ============================================================================
# Database Configuration (AC3)
# ============================================================================

variable "db_allocated_storage" {
  description = "Allocated storage for RDS in GB (e.g., 100)"
  type        = number
  default     = 100

  validation {
    condition     = var.db_allocated_storage >= 20 && var.db_allocated_storage <= 65536
    error_message = "Allocated storage must be between 20 GB and 65536 GB"
  }
}

variable "postgres_version" {
  description = "PostgreSQL engine version (e.g., 15.3, 16.0)"
  type        = string
  default     = "16.0"

  validation {
    condition     = can(regex("^15\\.[0-9]+|16\\.[0-9]+$", var.postgres_version))
    error_message = "PostgreSQL version must be 15.x or 16.x"
  }
}

variable "db_instance_class" {
  description = "RDS instance class (e.g., db.t3.medium, db.t4g.large)"
  type        = string
  default     = "db.t3.medium"
}

variable "db_name" {
  description = "Name of the default database to create"
  type        = string
  default     = "aiagents"

  validation {
    condition     = can(regex("^[a-z][a-z0-9_]*$", var.db_name)) && length(var.db_name) <= 63
    error_message = "Database name must start with letter, contain only lowercase letters/numbers/underscores, max 63 chars"
  }
}

variable "db_username" {
  description = "Master username for PostgreSQL (e.g., postgres, admin)"
  type        = string
  default     = "postgres"
  sensitive   = true

  validation {
    condition     = can(regex("^[a-z][a-z0-9_]*$", var.db_username)) && length(var.db_username) <= 16
    error_message = "Username must start with letter, contain only lowercase letters/numbers/underscores, max 16 chars"
  }
}

variable "db_password" {
  description = "Master password for PostgreSQL (minimum 8 characters, should be strong)"
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.db_password) >= 8
    error_message = "Password must be at least 8 characters"
  }
}

# ============================================================================
# Cache Configuration (AC4)
# ============================================================================

variable "redis_version" {
  description = "Redis engine version (e.g., 7.0, 7.1)"
  type        = string
  default     = "7.1"

  validation {
    condition     = can(regex("^7\\.[0-9]$", var.redis_version))
    error_message = "Redis version must be 7.x (e.g., 7.0, 7.1)"
  }
}

variable "cache_node_type" {
  description = "ElastiCache node type (e.g., cache.t3.micro, cache.t4g.small)"
  type        = string
  default     = "cache.t3.small"
}

variable "cache_num_clusters" {
  description = "Number of cache clusters (e.g., 2 for primary+replica, minimum 2 for HA)"
  type        = number
  default     = 2

  validation {
    condition     = var.cache_num_clusters >= 2 && var.cache_num_clusters <= 6
    error_message = "Cache clusters must be between 2 and 6 for HA"
  }
}

# ============================================================================
# Ingress and TLS Configuration (AC5)
# ============================================================================

variable "nginx_ingress_version" {
  description = "Helm chart version for nginx-ingress (e.g., 4.8.0)"
  type        = string
  default     = "4.8.0"
}

variable "cert_manager_version" {
  description = "Helm chart version for cert-manager (e.g., v1.13.0)"
  type        = string
  default     = "v1.13.0"
}

variable "letsencrypt_email" {
  description = "Email for Let's Encrypt certificate notifications"
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.letsencrypt_email))
    error_message = "Must be a valid email address"
  }
}

# ============================================================================
# Monitoring Configuration (AC6)
# ============================================================================

variable "log_retention_days" {
  description = "CloudWatch log retention period in days (e.g., 90 for compliance)"
  type        = number
  default     = 90

  validation {
    condition     = var.log_retention_days >= 1 && var.log_retention_days <= 3653
    error_message = "Log retention must be between 1 and 3653 days"
  }
}

variable "prometheus_endpoint" {
  description = "Prometheus endpoint for metrics collection (e.g., http://prometheus:9090)"
  type        = string
  default     = "http://prometheus.monitoring:9090"
}

variable "jaeger_endpoint" {
  description = "Jaeger endpoint for distributed tracing (e.g., jaeger-collector:14268)"
  type        = string
  default     = "jaeger-collector.tracing:14268"
}

# ============================================================================
# Tags and Labels
# ============================================================================

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "ai-agents"
    Environment = "production"
    ManagedBy   = "Terraform"
  }
}
