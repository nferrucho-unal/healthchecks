resource "random_password" "database" {
  length  = 32
  special = false
}

resource "random_id" "final_snapshot" {
  byte_length = 4
}

resource "aws_secretsmanager_secret" "database_password" {
  name                    = "${var.name_prefix}/database-password"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "database_password" {
  secret_id     = aws_secretsmanager_secret.database_password.id
  secret_string = random_password.database.result
}

resource "aws_db_subnet_group" "main" {
  name       = "${var.name_prefix}-db"
  subnet_ids = var.private_subnet_ids

  tags = { Name = "${var.name_prefix}-db" }
}

resource "aws_security_group" "database" {
  name_prefix = "${var.name_prefix}-db-"
  description = "Permite PostgreSQL solo desde las tareas ECS."
  vpc_id      = var.vpc_id

  ingress {
    description     = "PostgreSQL desde Healthchecks"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.application_security_group]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "postgres" {
  identifier                 = "${var.name_prefix}-postgres"
  engine                     = "postgres"
  engine_version             = "16"
  instance_class             = var.db_instance_class
  allocated_storage          = 20
  max_allocated_storage      = 100
  storage_type               = "gp3"
  storage_encrypted          = true
  db_name                    = var.db_name
  username                   = var.db_user
  password                   = random_password.database.result
  port                       = 5432
  db_subnet_group_name       = aws_db_subnet_group.main.name
  vpc_security_group_ids     = [aws_security_group.database.id]
  publicly_accessible        = false
  multi_az                   = false
  backup_retention_period    = 7
  auto_minor_version_upgrade = true
  deletion_protection        = true
  skip_final_snapshot        = false
  final_snapshot_identifier  = "${var.name_prefix}-final-${random_id.final_snapshot.hex}"

  depends_on = [aws_secretsmanager_secret_version.database_password]

  lifecycle {
    prevent_destroy = true
  }
}
