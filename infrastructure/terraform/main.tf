# Production Kubernetes Cluster Provisioning
# ============================================
#
# This Terraform configuration provisions a production-ready Kubernetes cluster
# with high availability, managed database, managed cache, and monitoring integration.
#
# Cloud Provider Selection (AC1):
# ==============================
# This configuration uses AWS EKS as the primary cloud provider, selected based on:
# - Mature Kubernetes service (EKS) with strong ecosystem support
# - Terraform aws-provider has extensive module library and community best practices
# - Compatible with GCP GKE and Azure AKS via cloud-agnostic patterns
# - Team has existing AWS experience from Docker infrastructure
#
# To use GCP GKE: Modify provider block to google, change resource types to google_container_cluster
# To use Azure AKS: Modify provider block to azurerm, change resource types to azurerm_kubernetes_cluster
#
# See: docs/operations/cloud-provider-comparison.md for detailed provider selection matrix

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
  }

  # Production: Uncomment to use remote state backend
  # backend "s3" {
  #   bucket         = "ai-agents-terraform-state"
  #   key            = "production/kubernetes/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "terraform-lock"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "ai-agents"
      Environment = "production"
      ManagedBy   = "Terraform"
      CreatedDate = timestamp()
    }
  }
}

# Kubernetes provider configuration - authenticated via EKS
provider "kubernetes" {
  host                   = module.eks_cluster.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks_cluster.cluster_ca_certificate)

  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", module.eks_cluster.cluster_name, "--region", var.aws_region]
  }
}

# Helm provider configuration for deploying Helm charts
provider "helm" {
  kubernetes {
    host                   = module.eks_cluster.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks_cluster.cluster_ca_certificate)

    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", module.eks_cluster.cluster_name, "--region", var.aws_region]
    }
  }
}

# ============================================================================
# Core Infrastructure Modules
# ============================================================================

# VPC for cluster networking - provides network isolation and security boundaries
module "vpc" {
  source = "./modules/vpc"

  cluster_name = var.cluster_name
  cidr_block   = var.vpc_cidr_block
  region       = var.aws_region

  # Availability zones for high availability
  availability_zones = data.aws_availability_zones.available.names

  tags = {
    Name = "${var.cluster_name}-vpc"
  }
}

# EKS Cluster - managed Kubernetes control plane
# AC1, AC2: Cloud Provider Cluster Provisioned with HA configuration
module "eks_cluster" {
  source = "./modules/eks-cluster"

  cluster_name    = var.cluster_name
  cluster_version = var.kubernetes_version
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnet_ids

  # HA configuration: 3+ nodes across multiple AZs
  node_groups = {
    default = {
      min_size       = var.min_node_count
      max_size       = var.max_node_count
      desired_size   = var.desired_node_count
      instance_types = var.node_instance_types

      # Spread nodes across availability zones
      subnet_ids = module.vpc.private_subnet_ids
    }
  }

  # Enable control plane logging for audit and troubleshooting
  cluster_enabled_log_types = [
    "api",
    "audit",
    "authenticator",
    "controllerManager",
    "scheduler"
  ]

  tags = {
    Name = var.cluster_name
  }
}

# Managed PostgreSQL Database
# AC3: Production-grade PostgreSQL with automated backups, encryption, failover
module "rds_postgresql" {
  source = "./modules/rds-postgresql"

  identifier         = "${var.cluster_name}-postgres"
  allocated_storage  = var.db_allocated_storage
  engine_version     = var.postgres_version
  instance_class     = var.db_instance_class
  db_name            = var.db_name
  db_username        = var.db_username
  db_password        = var.db_password
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.database_subnet_ids

  # High availability: Multi-AZ deployment with automatic failover
  multi_az = true

  # Automated backups
  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "mon:04:00-mon:05:00"

  # Encryption at rest with AWS KMS
  storage_encrypted = true
  kms_key_id        = aws_kms_key.rds_key.arn

  # Enable enhanced monitoring
  performance_insights_enabled = true
  monitoring_interval         = 60
  monitoring_role_arn         = aws_iam_role.rds_monitoring_role.arn

  # Security
  publicly_accessible = false
  skip_final_snapshot = false
  final_snapshot_identifier = "${var.cluster_name}-postgres-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  tags = {
    Name = "${var.cluster_name}-postgres"
  }
}

# Managed Redis Cache
# AC4: Production Redis with persistence, replication, failover
module "elasticache_redis" {
  source = "./modules/elasticache-redis"

  identifier              = "${var.cluster_name}-redis"
  engine_version          = var.redis_version
  node_type              = var.cache_node_type
  num_cache_clusters     = var.cache_num_clusters
  vpc_id                 = module.vpc.vpc_id
  subnet_ids             = module.vpc.cache_subnet_ids

  # High availability: Multi-AZ automatic failover
  automatic_failover_enabled = true
  multi_az_enabled          = true

  # Persistence: RDB snapshots for durability
  snapshot_retention_limit = 5
  snapshot_window         = "03:00-05:00"

  # Encryption
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  kms_key_id                = aws_kms_key.elasticache_key.arn

  # Eviction policy: allkeys-lru for message queue + caching
  eviction_policy = "allkeys-lru"

  # Performance: Enable parameter group optimization
  parameter_group_family = "redis7"

  tags = {
    Name = "${var.cluster_name}-redis"
  }
}

# ============================================================================
# Ingress and TLS Configuration
# ============================================================================

# Ingress Controller - cloud-agnostic via Nginx
# AC5: Ingress with TLS certificates
module "ingress_controller" {
  source = "./modules/ingress-controller"

  cluster_name           = module.eks_cluster.cluster_name
  namespace              = "ingress-nginx"
  helm_chart_version     = var.nginx_ingress_version
  load_balancer_type     = "nlb"  # Network Load Balancer for performance

  depends_on = [module.eks_cluster]
}

# Cert-Manager for automatic TLS certificate provisioning
# AC5: Let's Encrypt ACME issuer
module "cert_manager" {
  source = "./modules/cert-manager"

  cluster_name       = module.eks_cluster.cluster_name
  namespace          = "cert-manager"
  helm_chart_version = var.cert_manager_version
  email              = var.letsencrypt_email

  depends_on = [module.eks_cluster]
}

# ============================================================================
# Monitoring and Observability
# ============================================================================

# CloudWatch Container Insights for cluster monitoring
# AC6: Cloud Monitoring Integration
resource "aws_cloudwatch_log_group" "cluster_logs" {
  name              = "/aws/eks/${var.cluster_name}"
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${var.cluster_name}-logs"
  }
}

# OTEL Collector for distributed tracing integration with existing Prometheus/Grafana
# This bridges cluster metrics to external monitoring
module "otel_collector" {
  source = "./modules/otel-collector"

  cluster_name       = module.eks_cluster.cluster_name
  namespace          = "observability"
  prometheus_endpoint = var.prometheus_endpoint
  jaeger_endpoint     = var.jaeger_endpoint

  depends_on = [module.eks_cluster]
}

# ============================================================================
# Security Configuration
# ============================================================================

# KMS Keys for encryption
resource "aws_kms_key" "rds_key" {
  description             = "KMS key for RDS encryption"
  deletion_window_in_days = 10
  enable_key_rotation     = true

  tags = {
    Name = "${var.cluster_name}-rds-key"
  }
}

resource "aws_kms_key" "elasticache_key" {
  description             = "KMS key for ElastiCache encryption"
  deletion_window_in_days = 10
  enable_key_rotation     = true

  tags = {
    Name = "${var.cluster_name}-elasticache-key"
  }
}

# IAM role for RDS enhanced monitoring
resource "aws_iam_role" "rds_monitoring_role" {
  name = "${var.cluster_name}-rds-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "rds_monitoring_policy" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
  role       = aws_iam_role.rds_monitoring_role.name
}

# ============================================================================
# Data Sources
# ============================================================================

data "aws_availability_zones" "available" {
  state = "available"
}
