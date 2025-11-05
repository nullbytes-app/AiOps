# ============================================================================
# ElastiCache Redis Module - Managed Cache Service (AC4)
# ============================================================================

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.identifier}-subnet-group"
  subnet_ids = var.subnet_ids
}

resource "aws_elasticache_parameter_group" "main" {
  family = var.parameter_group_family
  name   = "${var.identifier}-params"

  parameter {
    name  = "maxmemory-policy"
    value = var.eviction_policy
  }

  parameter {
    name  = "timeout"
    value = "300"
  }
}

resource "aws_elasticache_replication_group" "main" {
  replication_group_description = "Redis for AI Agents"
  engine                        = "redis"
  engine_version                = var.engine_version
  node_type                     = var.node_type
  num_cache_clusters            = var.num_cache_clusters
  parameter_group_name          = aws_elasticache_parameter_group.main.name
  port                          = 6379
  subnet_group_name             = aws_elasticache_subnet_group.main.name
  security_group_ids            = [aws_security_group.elasticache.id]

  # HA Configuration (AC4)
  automatic_failover_enabled = var.automatic_failover_enabled
  multi_az_enabled          = var.multi_az_enabled

  # Persistence (AC4)
  snapshot_retention_limit = var.snapshot_retention_limit
  snapshot_window         = var.snapshot_window

  # Encryption (AC4)
  at_rest_encryption_enabled = var.at_rest_encryption_enabled
  transit_encryption_enabled = var.transit_encryption_enabled
  kms_key_id                = var.kms_key_id

  # Logging
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.main.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "slow-log"
  }

  auto_minor_version_upgrade = true

  tags = {
    Name = var.identifier
  }

  depends_on = [aws_elasticache_parameter_group.main]
}

resource "aws_cloudwatch_log_group" "main" {
  name              = "/aws/elasticache/${var.identifier}"
  retention_in_days = 7

  tags = {
    Name = "${var.identifier}-logs"
  }
}

resource "aws_security_group" "elasticache" {
  name        = "${var.identifier}-sg"
  description = "Security group for ElastiCache"
  vpc_id      = data.aws_subnet.main.vpc_id

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

data "aws_subnet" "main" {
  id = var.subnet_ids[0]
}
