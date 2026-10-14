module "networking" {
  source      = "./modules/networking"
  name_prefix = var.name_prefix
  vpc_cidr    = var.vpc_cidr
}

module "database" {
  source                     = "./modules/database"
  name_prefix                = var.name_prefix
  vpc_id                     = module.networking.vpc_id
  private_subnet_ids         = module.networking.private_subnet_ids
  application_security_group = module.compute.task_security_group_id
  db_name                    = var.db_name
  db_user                    = var.db_user
  db_instance_class          = var.db_instance_class
}

module "compute" {
  source                 = "./modules/compute"
  name_prefix            = var.name_prefix
  vpc_id                 = module.networking.vpc_id
  public_subnet_ids      = module.networking.public_subnet_ids
  image_tag              = var.image_tag
  desired_count          = var.desired_count
  aws_region             = var.aws_region
  db_endpoint            = module.database.db_endpoint
  db_port                = module.database.db_port
  db_name                = var.db_name
  db_user                = var.db_user
  db_password_secret_arn = module.database.db_password_secret_arn
}
