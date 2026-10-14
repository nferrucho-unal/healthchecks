variable "name_prefix" {
  type        = string
  description = "Prefijo de nombres de los recursos de datos."
}

variable "vpc_id" {
  type        = string
  description = "VPC donde se crea RDS."
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Subredes privadas para RDS."
}

variable "application_security_group" {
  type        = string
  description = "Grupo de seguridad de las tareas ECS autorizadas a conectarse a RDS."
}

variable "db_name" {
  type        = string
  description = "Nombre de la base PostgreSQL."
}

variable "db_user" {
  type        = string
  description = "Usuario PostgreSQL de la aplicación."
}

variable "db_instance_class" {
  type        = string
  description = "Clase de instancia RDS PostgreSQL."
}
