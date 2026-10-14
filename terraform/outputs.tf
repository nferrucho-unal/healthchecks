output "service_url" {
  description = "URL HTTP pública de Healthchecks."
  value       = module.compute.service_url
}

output "database_endpoint" {
  description = "Endpoint privado de RDS PostgreSQL."
  value       = module.database.db_endpoint
}

output "ecs_cluster_name" {
  description = "Nombre del clúster ECS."
  value       = module.compute.cluster_name
}
