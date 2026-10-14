output "db_endpoint" {
  description = "Hostname privado de RDS PostgreSQL."
  value       = aws_db_instance.postgres.address
}

output "db_port" {
  description = "Puerto de RDS PostgreSQL."
  value       = aws_db_instance.postgres.port
}

output "db_password_secret_arn" {
  description = "ARN del secreto de contraseña consumido por ECS."
  value       = aws_secretsmanager_secret.database_password.arn
}
