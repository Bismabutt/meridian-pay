variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "cluster_version" {
  description = "Kubernetes version. One or two minors behind latest, for ecosystem support."
  type        = string
  default     = "1.30"
}

variable "vpc_id" {
  description = "VPC the cluster runs in"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnets for worker nodes"
  type        = list(string)
}

variable "public_subnet_ids" {
  description = "Public subnets, so EKS can place internet-facing load balancers"
  type        = list(string)
}

variable "node_instance_types" {
  description = "Instance types for the node group. t3.medium keeps dev cost down."
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_desired_size" {
  type    = number
  default = 2
}

variable "node_min_size" {
  type    = number
  default = 2
}

variable "node_max_size" {
  type    = number
  default = 4
}

variable "node_capacity_type" {
  description = "ON_DEMAND or SPOT. Spot is roughly 70 percent cheaper but can be reclaimed."
  type        = string
  default     = "SPOT"
}

variable "endpoint_public_access" {
  description = "Whether the Kubernetes API is reachable from the internet. Needed for kubectl from a laptop."
  type        = bool
  default     = true
}