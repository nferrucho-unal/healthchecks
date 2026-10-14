# 1. Capa de Red
module "networking" {
  source = "./modules/networking"
  vpc_cidr = "10.0.0.0/16"
}

# 2. Capa de Persistencia (Desacoplada)
module "database" {
  source             = "./modules/database"
  vpc_id             = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
  db_user            = var.db_user
  db_password        = var.db_password # Variable sensible
}

# 3. Capa de Cómputo
module "compute" {
  source            = "./modules/compute"
  vpc_id            = module.networking.vpc_id
  public_subnet_ids = module.networking.public_subnet_ids
  
  # Inyección de parámetros de conexión de forma externa
  database_url      = module.database.db_endpoint
  database_user     = var.db_user
  database_password = var.db_password
}
