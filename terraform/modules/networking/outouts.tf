output "vpc_id" {
  description = "ID de la VPC creada."
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Subredes públicas para ALB y tareas ECS."
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Subredes privadas para RDS."
  value       = aws_subnet.private[*].id
}