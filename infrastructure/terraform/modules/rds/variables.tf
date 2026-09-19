variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  description = "Databases sit in private subnets with no route from the internet"
  type        = list(string)
}

variable "allowed_security_group_ids" {
  description = "Security groups permitted to reach the databases, normally the EKS nodes"
  type        = list(string)
}

variable "engine_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "15.7"
}

variable "databases" {
  description = "One entry per service. Sizing follows the criticality tiers in the service decomposition."
  type = map(object({
    instance_class        = string
    allocated_storage     = number
    multi_az              = bool
    backup_retention_days = number
    deletion_protection   = bool
  }))
}

variable "master_username" {
  type    = string
  default = "meridian_app"
}