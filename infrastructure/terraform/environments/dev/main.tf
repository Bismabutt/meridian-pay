provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

module "network" {
  source = "../../modules/network"

  project_name = var.project_name
  environment  = var.environment

  vpc_cidr             = "10.0.0.0/16"
  availability_zones   = ["eu-west-2a", "eu-west-2b", "eu-west-2c"]
  public_subnet_cidrs  = ["10.0.0.0/20", "10.0.16.0/20", "10.0.32.0/20"]
  private_subnet_cidrs = ["10.0.48.0/20", "10.0.64.0/20", "10.0.80.0/20"]

  # One NAT in dev. Production would use one per AZ.
  single_nat_gateway = true
}

module "eks" {
  source = "../../modules/eks"

  project_name = var.project_name
  environment  = var.environment

  cluster_version    = "1.30"
  vpc_id             = module.network.vpc_id
  private_subnet_ids = module.network.private_subnet_ids
  public_subnet_ids  = module.network.public_subnet_ids

  # Dev sizing. Spot for cost; production would use on-demand for the money zone.
  node_instance_types = ["t3.medium"]
  node_capacity_type  = "SPOT"
  node_desired_size   = 2
  node_min_size       = 2
  node_max_size       = 4

  endpoint_public_access = true
}

module "rds" {
  source = "../../modules/rds"

  project_name = var.project_name
  environment  = var.environment

  vpc_id                     = module.network.vpc_id
  private_subnet_ids         = module.network.private_subnet_ids
  allowed_security_group_ids = [module.eks.cluster_security_group_id]

  engine_version = "15.7"

  # Sizing follows the criticality tiers in the service decomposition.
  databases = {
    ledger = {
      instance_class        = "db.t4g.small"
      allocated_storage     = 20
      multi_az              = true
      backup_retention_days = 7
      deletion_protection   = false
    }
    payment = {
      instance_class        = "db.t4g.small"
      allocated_storage     = 20
      multi_az              = true
      backup_retention_days = 7
      deletion_protection   = false
    }
    auth = {
      instance_class        = "db.t4g.micro"
      allocated_storage     = 20
      multi_az              = false
      backup_retention_days = 3
      deletion_protection   = false
    }
    account = {
      instance_class        = "db.t4g.small"
      allocated_storage     = 20
      multi_az              = false
      backup_retention_days = 3
      deletion_protection   = false
    }
    fraud = {
      instance_class        = "db.t4g.micro"
      allocated_storage     = 20
      multi_az              = false
      backup_retention_days = 1
      deletion_protection   = false
    }
    fx = {
      instance_class        = "db.t4g.micro"
      allocated_storage     = 20
      multi_az              = false
      backup_retention_days = 1
      deletion_protection   = false
    }
    notification = {
      instance_class        = "db.t4g.micro"
      allocated_storage     = 20
      multi_az              = false
      backup_retention_days = 1
      deletion_protection   = false
    }
  }
}

module "redis" {
  source = "../../modules/redis"

  project_name = var.project_name
  environment  = var.environment

  vpc_id                     = module.network.vpc_id
  private_subnet_ids         = module.network.private_subnet_ids
  allowed_security_group_ids = [module.eks.cluster_security_group_id]

  node_type       = "cache.t4g.micro"
  engine_version  = "7.1"
  num_cache_nodes = 1
}

module "ecr" {
  source = "../../modules/ecr"

  project_name = var.project_name

  repositories = [
    "api-gateway",
    "auth-service",
    "account-service",
    "payment-service",
    "ledger-service",
    "fraud-service",
    "fx-service",
    "notification-service",
  ]

  image_retention_count = 10
  scan_on_push          = true
}