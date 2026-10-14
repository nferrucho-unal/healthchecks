variable "aws_region" {
  type        = string
  description = "Región de AWS donde se desplegará la infraestructura."
  default     = "us-east-1"
}

variable "name_prefix" {
  type        = string
  description = "Prefijo para nombrar los recursos AWS."
  default     = "healthchecks"
}

variable "vpc_cidr" {
  type        = string
  description = "Rango IPv4 de la VPC."
  default     = "10.0.0.0/16"
}

variable "db_name" {
  type        = string
  description = "Nombre de la base PostgreSQL."
  default     = "healthchecks"
}

variable "db_user" {
  type        = string
  description = "Usuario de la aplicación en PostgreSQL."
  default     = "hc"
}

variable "db_instance_class" {
  type        = string
  description = "Clase de instancia RDS PostgreSQL."
  default     = "db.t3.micro"
}

variable "image_tag" {
  type        = string
  description = "Tag inmutable/versionado de healthchecks/healthchecks; no se usa latest."

  validation {
    condition     = can(regex("^(v[0-9]+\\.[0-9]+(\\.[0-9]+)?|sha-[0-9a-f]{7,40})$", var.image_tag))
    error_message = "Use un tag de versión (por ejemplo vX.Y) o un tag sha-<commit> publicado en Docker Hub."
  }
}

variable "desired_count" {
  type        = number
  description = "Cantidad de tareas ECS de Healthchecks."
  default     = 1
}
