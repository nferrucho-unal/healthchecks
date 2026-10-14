variable "name_prefix" {
  type        = string
  description = "Prefijo de nombres de los recursos de red."
}

variable "vpc_cidr" {
  type        = string
  description = "Rango IPv4 de la VPC."
}
