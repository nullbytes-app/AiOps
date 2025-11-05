variable "identifier" {
  type = string
}

variable "engine_version" {
  type = string
}

variable "node_type" {
  type = string
}

variable "num_cache_clusters" {
  type = number
}

variable "vpc_id" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "automatic_failover_enabled" {
  type = bool
}

variable "multi_az_enabled" {
  type = bool
}

variable "snapshot_retention_limit" {
  type = number
}

variable "snapshot_window" {
  type = string
}

variable "at_rest_encryption_enabled" {
  type = bool
}

variable "transit_encryption_enabled" {
  type = bool
}

variable "kms_key_id" {
  type = string
}

variable "eviction_policy" {
  type = string
}

variable "parameter_group_family" {
  type = string
}
