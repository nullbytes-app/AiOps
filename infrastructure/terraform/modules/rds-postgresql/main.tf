# ============================================================================
# RDS PostgreSQL Module - Managed Database Service
# ============================================================================

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Database subnet group
resource "aws_db_subnet_group" "main" {
  name       = "${var.identifier}-subnet-group"
  subnet_ids = var.subnet_ids

  tags = {
    Name = "${var.identifier}-subnet-group"
  }
}

# RDS Instance
resource "aws_db_instance" "main" {
  identifier            = var.identifier
  allocated_storage     = var.allocated_storage
  storage_type          = "gp3"
  engine                = "postgres"
  engine_version        = var.engine_version
  instance_class        = var.instance_class
  db_name               = var.db_name
  username              = var.db_username
  password              = var.db_password
  publicly_accessible   = var.publicly_accessible
  skip_final_snapshot   = var.skip_final_snapshot
  final_snapshot_identifier = var.final_snapshot_identifier

  # HA Configuration
  multi_az = var.multi_az

  # Backup configuration (AC3)
  backup_retention_period = var.backup_retention_period
  backup_window          = var.backup_window
  copy_tags_to_snapshot  = true

  # Encryption (AC3)
  storage_encrypted = var.storage_encrypted
  kms_key_id        = var.kms_key_id

  # Networking
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  # Maintenance
  maintenance_window = var.maintenance_window
  auto_minor_version_upgrade = true

  # Monitoring
  performance_insights_enabled = var.performance_insights_enabled
  monitoring_interval         = var.monitoring_interval
  monitoring_role_arn         = var.monitoring_role_arn
  enabled_cloudwatch_logs_exports = ["postgresql"]

  # Parameters for row-level security (AC3)
  parameter_group_name = aws_db_parameter_group.main.name

  depends_on = [aws_db_parameter_group.main]

  tags = {
    Name = var.identifier
  }
}

# Parameter group for RLS
resource "aws_db_parameter_group" "main" {
  family = "postgres${split(".", var.engine_version)[0]}"
  name   = "${var.identifier}-params"

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  parameter {
    name  = "log_statement"
    value = "all"
  }

  tags = {
    Name = "${var.identifier}-params"
  }
}

# Security group
resource "aws_security_group" "rds" {
  name        = "${var.identifier}-sg"
  description = "Security group for RDS"
  vpc_id      = data.aws_subnet.main.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
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
