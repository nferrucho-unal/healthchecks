output "service_url" {
  description = "URL HTTP pública del balanceador."
  value       = "http://${aws_lb.web.dns_name}"
}

output "cluster_name" {
  description = "Nombre del clúster ECS."
  value       = aws_ecs_cluster.main.name
}

output "task_security_group_id" {
  description = "Grupo de seguridad para las tareas ECS."
  value       = aws_security_group.task.id
}
