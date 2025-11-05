variable "identifier" {
  type = string
}

variable "allocated_storage" {
  type = number
}

variable "engine_version" {
  type = string
}

variable "instance_class" {
  type = string
}

variable "db_name" {
  type = string
}

variable "db_username" {
  type      = string
  sensitive = true
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "vpc_id" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "multi_az" {
  type    = bool
  default = true
}

variable "backup_retention_period" {
  type = number
}

variable "backup_window" {
  type = string
}

variable "maintenance_window" {
  type = string
}

variable "storage_encrypted" {
  type = bool
}

variable "kms_key_id" {
  type = string
}

variable "publicly_accessible" {
  type    = bool
  default = false
}

variable "skip_final_snapshot" {
  type = bool
}

variable "final_snapshot_identifier" {
  type = string
}

variable "performance_insights_enabled" {
  type = bool
}

variable "monitoring_interval" {
  type = number
}

variable "monitoring_role_arn" {
  type = string
}
