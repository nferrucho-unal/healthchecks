# variables.tf en la raíz
variable "db_user" {
  type        = string
  description = "Usuario administrador de la BD"
}

variable "db_password" {
  type        = string
  description = "Contraseña de la BD"
  sensitive   = true # Oculta el valor en logs y terminal
}
