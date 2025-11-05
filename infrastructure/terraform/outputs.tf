# ============================================================================
# Terraform Outputs for Production Kubernetes Cluster
# ============================================================================
#
# These outputs expose critical infrastructure values for cluster access,
# application configuration, and verification procedures.
#

# ============================================================================
# Kubernetes Cluster Outputs
# ============================================================================

output "cluster_name" {
  description = "Name of the EKS cluster"
  value       = module.eks_cluster.cluster_name
}

output "cluster_endpoint" {
  description = "Kubernetes API endpoint (used to connect with kubectl)"
  value       = module.eks_cluster.cluster_endpoint
  sensitive   = false
}

output "cluster_ca_certificate" {
  description = "Base64 encoded certificate authority certificate (for kubectl config)"
  value       = module.eks_cluster.cluster_ca_certificate
  sensitive   = true
}

output "cluster_arn" {
  description = "ARN of the EKS cluster"
  value       = module.eks_cluster.cluster_arn
}

output "cluster_version" {
  description = "Kubernetes version of the cluster"
  value       = module.eks_cluster.cluster_version
}

output "configure_kubectl" {
  description = "Command to configure kubectl context for this cluster"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks_cluster.cluster_name}"
}

# ============================================================================
# VPC and Networking Outputs
# ============================================================================

output "vpc_id" {
  description = "VPC ID where cluster is deployed"
  value       = module.vpc.vpc_id
}

output "vpc_cidr" {
  description = "CIDR block of the VPC"
  value       = module.vpc.vpc_cidr
}

output "subnet_ids_public" {
  description = "Public subnet IDs for ingress controller and NAT gateways"
  value       = module.vpc.public_subnet_ids
}

output "subnet_ids_private" {
  description = "Private subnet IDs for cluster worker nodes"
  value       = module.vpc.private_subnet_ids
}

output "availability_zones" {
  description = "Availability zones where cluster is deployed (for HA verification)"
  value       = data.aws_availability_zones.available.names
}

# ============================================================================
# Database Outputs (AC3)
# ============================================================================

output "rds_endpoint" {
  description = "PostgreSQL database endpoint (hostname:port)"
  value       = module.rds_postgresql.endpoint
  sensitive   = false
}

output "rds_hostname" {
  description = "PostgreSQL hostname for connection string"
  value       = module.rds_postgresql.hostname
  sensitive   = false
}

output "rds_port" {
  description = "PostgreSQL port (default 5432)"
  value       = module.rds_postgresql.port
  sensitive   = false
}

output "rds_database_name" {
  description = "Default database name"
  value       = module.rds_postgresql.database_name
  sensitive   = false
}

output "rds_username" {
  description = "PostgreSQL master username"
  value       = module.rds_postgresql.username
  sensitive   = true
}

output "rds_arn" {
  description = "ARN of the RDS instance"
  value       = module.rds_postgresql.arn
}

output "database_connection_string_template" {
  description = "Template for application database connection string (replace PASSWORD with actual secret)"
  value       = "postgresql://${module.rds_postgresql.username}:PASSWORD@${module.rds_postgresql.endpoint}/${module.rds_postgresql.database_name}"
  sensitive   = false
}

# ============================================================================
# Cache Outputs (AC4)
# ============================================================================

output "elasticache_endpoint" {
  description = "ElastiCache Redis primary endpoint (hostname:port)"
  value       = module.elasticache_redis.primary_endpoint
  sensitive   = false
}

output "elasticache_hostname" {
  description = "Redis hostname for cache connection"
  value       = module.elasticache_redis.primary_hostname
  sensitive   = false
}

output "elasticache_port" {
  description = "Redis port (default 6379)"
  value       = module.elasticache_redis.port
  sensitive   = false
}

output "elasticache_configuration_endpoint" {
  description = "Redis configuration endpoint (for replication info)"
  value       = module.elasticache_redis.configuration_endpoint
  sensitive   = false
}

output "cache_connection_string_template" {
  description = "Template for application cache connection string"
  value       = "redis://:/PASSWORD@${module.elasticache_redis.primary_endpoint}"
  sensitive   = false
}

# ============================================================================
# Ingress and TLS Outputs (AC5)
# ============================================================================

output "ingress_controller_service_endpoint" {
  description = "External IP/hostname of ingress controller (AWS NLB)"
  value       = module.ingress_controller.load_balancer_dns
  sensitive   = false
}

output "ingress_controller_namespace" {
  description = "Kubernetes namespace for ingress controller"
  value       = module.ingress_controller.namespace
}

output "configure_dns_records" {
  description = "Instructions for DNS configuration"
  value       = <<-EOT
    To configure DNS for your domain:
    1. Get the ingress NLB endpoint: ${module.ingress_controller.load_balancer_dns}
    2. Create CNAME record: yourdomain.com -> ${module.ingress_controller.load_balancer_dns}
    3. Wait for DNS propagation (usually 1-5 minutes)
    4. Cert-manager will automatically provision Let's Encrypt certificate via ACME challenge
  EOT
}

output "cert_manager_namespace" {
  description = "Kubernetes namespace for cert-manager"
  value       = module.cert_manager.namespace
}

# ============================================================================
# Monitoring and Observability Outputs (AC6)
# ============================================================================

output "cloudwatch_log_group_name" {
  description = "CloudWatch log group name for cluster logs"
  value       = aws_cloudwatch_log_group.cluster_logs.name
}

output "cloudwatch_log_group_arn" {
  description = "CloudWatch log group ARN"
  value       = aws_cloudwatch_log_group.cluster_logs.arn
}

output "view_logs_command" {
  description = "AWS CLI command to view recent cluster logs"
  value       = "aws logs tail ${aws_cloudwatch_log_group.cluster_logs.name} --follow"
}

output "otel_collector_namespace" {
  description = "Kubernetes namespace for OpenTelemetry collector"
  value       = module.otel_collector.namespace
}

# ============================================================================
# Security and Encryption Outputs
# ============================================================================

output "rds_kms_key_id" {
  description = "AWS KMS key ID for RDS encryption"
  value       = aws_kms_key.rds_key.id
}

output "elasticache_kms_key_id" {
  description = "AWS KMS key ID for ElastiCache encryption"
  value       = aws_kms_key.elasticache_key.id
}

output "rds_monitoring_role_arn" {
  description = "IAM role ARN for RDS enhanced monitoring"
  value       = aws_iam_role.rds_monitoring_role.arn
}

# ============================================================================
# Verification and Next Steps
# ============================================================================

output "next_steps" {
  description = "Summary of next steps after infrastructure creation"
  value       = <<-EOT
    ============================================================
    Production Kubernetes Cluster Provisioning Complete!
    ============================================================

    1. CONFIGURE kubectl:
       ${self.configure_kubectl}

    2. VERIFY CLUSTER:
       kubectl get nodes          # Should show 3+ nodes Ready
       kubectl cluster-info       # Should show healthy control plane

    3. CONFIGURE INGRESS:
       ${self.configure_dns_records}

    4. VERIFY DATABASE:
       # From any pod in the cluster:
       kubectl run -it --rm debug --image=postgres:16 --restart=Never -- \
         psql -h ${module.rds_postgresql.endpoint} -U ${module.rds_postgresql.username} -d ${module.rds_postgresql.database_name}

    5. VERIFY CACHE:
       # From any pod in the cluster:
       kubectl run -it --rm debug --image=redis:7 --restart=Never -- \
         redis-cli -h ${module.elasticache_redis.primary_hostname} -p ${module.elasticache_redis.port}

    6. VIEW CLUSTER LOGS:
       ${self.view_logs_command}

    7. DEPLOY APPLICATION:
       kubectl apply -f k8s/production/

    8. MONITOR DEPLOYMENT:
       kubectl get all -n default
       kubectl describe pod <pod-name>

    ============================================================
  EOT
}
