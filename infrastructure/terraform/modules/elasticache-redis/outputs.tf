output "primary_endpoint" {
  value = aws_elasticache_replication_group.main.primary_endpoint_address
}

output "primary_hostname" {
  value = aws_elasticache_replication_group.main.primary_endpoint_address
}

output "configuration_endpoint" {
  value = aws_elasticache_replication_group.main.configuration_endpoint_address
}

output "port" {
  value = aws_elasticache_replication_group.main.port
}
