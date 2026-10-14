variable "name_prefix" {
  type        = string
  description = "Prefijo de nombres de los recursos de cómputo."
}

variable "vpc_id" {
  type        = string
  description = "VPC donde se despliega ECS y el balanceador."
}

variable "public_subnet_ids" {
  type        = list(string)
  description = "Subredes públicas para el ALB y las tareas Fargate."
}

variable "image_tag" {
  type        = string
  description = "Tag versionado de la imagen de Healthchecks."
}

variable "desired_count" {
  type        = number
  description = "Cantidad de tareas ECS."
}

variable "db_endpoint" {
  type        = string
  description = "Hostname privado de RDS."
}

variable "db_port" {
  type        = number
  description = "Puerto de RDS."
}

variable "db_name" {
  type        = string
  description = "Nombre de la base de datos."
}

variable "db_user" {
  type        = string
  description = "Usuario de la base de datos."
}

variable "db_password_secret_arn" {
  type        = string
  description = "ARN del secreto de contraseña de PostgreSQL."
}

variable "aws_region" {
  type        = string
  description = "Región usada para los logs de CloudWatch."
}
