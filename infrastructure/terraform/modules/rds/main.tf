locals {
  name = "${var.project_name}-${var.environment}"
}

# ------------------------------------------------------------
# Subnet group — tells RDS which subnets it may use
# ------------------------------------------------------------

resource "aws_db_subnet_group" "main" {
  name       = "${local.name}-db-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name = "${local.name}-db-subnet-group"
  }
}

# ------------------------------------------------------------
# Security group — only the cluster may connect
# ------------------------------------------------------------

resource "aws_security_group" "database" {
  name        = "${local.name}-database-sg"
  description = "PostgreSQL access, restricted to the EKS cluster"
  vpc_id      = var.vpc_id

  tags = {
    Name = "${local.name}-database-sg"
  }
}

resource "aws_vpc_security_group_ingress_rule" "postgres" {
  count = length(var.allowed_security_group_ids)

  security_group_id            = aws_security_group.database.id
  referenced_security_group_id = var.allowed_security_group_ids[count.index]
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  description                  = "PostgreSQL from the cluster"
}

# ------------------------------------------------------------
# Master passwords, generated and stored in Secrets Manager
# ------------------------------------------------------------

resource "random_password" "master" {
  for_each = var.databases

  length  = 32
  special = true
  # Characters RDS rejects in a master password
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "aws_secretsmanager_secret" "db" {
  for_each = var.databases

  name                    = "${local.name}/rds/${each.key}"
  description             = "Master credentials for the ${each.key} database"
  recovery_window_in_days = 0 # dev only, allows immediate deletion

  tags = {
    Name    = "${local.name}-${each.key}-credentials"
    Service = each.key
  }
}

resource "aws_secretsmanager_secret_version" "db" {
  for_each = var.databases

  secret_id = aws_secretsmanager_secret.db[each.key].id
  secret_string = jsonencode({
    username = var.master_username
    password = random_password.master[each.key].result
    engine   = "postgres"
    host     = aws_db_instance.main[each.key].address
    port     = 5432
    dbname   = replace(each.key, "-", "_")
  })
}

# ------------------------------------------------------------
# One instance per service
# ------------------------------------------------------------

resource "aws_db_instance" "main" {
  for_each = var.databases

  identifier     = "${local.name}-${each.key}"
  engine         = "postgres"
  engine_version = var.engine_version
  instance_class = each.value.instance_class

  allocated_storage     = each.value.allocated_storage
  max_allocated_storage = each.value.allocated_storage * 4 # storage autoscaling
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = replace(each.key, "-", "_")
  username = var.master_username
  password = random_password.master[each.key].result
  port     = 5432

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.database.id]
  publicly_accessible    = false

  multi_az                = each.value.multi_az
  backup_retention_period = each.value.backup_retention_days
  backup_window           = "02:00-03:00"
  maintenance_window      = "sun:03:30-sun:04:30"

  # Point in time recovery is implied by backup retention above zero
  copy_tags_to_snapshot = true

  deletion_protection          = each.value.deletion_protection
  skip_final_snapshot          = true  # dev only
  performance_insights_enabled = false # costs extra on small instances

  auto_minor_version_upgrade = true

  tags = {
    Name    = "${local.name}-${each.key}"
    Service = each.key
  }
}