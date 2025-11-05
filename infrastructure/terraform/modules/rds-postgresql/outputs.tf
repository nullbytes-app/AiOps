output "endpoint" {
  value = aws_db_instance.main.endpoint
}

output "hostname" {
  value = aws_db_instance.main.address
}

output "port" {
  value = aws_db_instance.main.port
}

output "database_name" {
  value = aws_db_instance.main.db_name
}

output "username" {
  value     = aws_db_instance.main.username
  sensitive = true
}

output "arn" {
  value = aws_db_instance.main.arn
}
