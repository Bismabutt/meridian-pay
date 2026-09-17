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
  type = list(string)
}

variable "allowed_security_group_ids" {
  description = "Security groups permitted to reach Redis, normally the EKS nodes"
  type        = list(string)
}

variable "node_type" {
  description = "Instance size. t4g.micro is sufficient for sessions and idempotency keys in dev."
  type        = string
  default     = "cache.t4g.micro"
}

variable "engine_version" {
  type    = string
  default = "7.1"
}

variable "num_cache_nodes" {
  description = "One node in dev. Production would use a replication group with automatic failover."
  type        = number
  default     = 1
}