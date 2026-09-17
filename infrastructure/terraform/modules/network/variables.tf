variable "project_name" {
  description = "Project name, used as a prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name, for example dev or prod"
  type        = string
}

variable "vpc_cidr" {
  description = "IP range for the VPC. Cannot be changed after creation."
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "AZs to spread subnets across. Three for production-grade resilience."
  type        = list(string)
  default     = ["eu-west-2a", "eu-west-2b", "eu-west-2c"]
}

variable "public_subnet_cidrs" {
  description = "One public subnet per AZ. Load balancer and NAT live here."
  type        = list(string)
  default     = ["10.0.0.0/20", "10.0.16.0/20", "10.0.32.0/20"]
}

variable "private_subnet_cidrs" {
  description = "One private subnet per AZ. Nodes and databases live here."
  type        = list(string)
  default     = ["10.0.48.0/20", "10.0.64.0/20", "10.0.80.0/20"]
}

variable "single_nat_gateway" {
  description = "One NAT instead of one per AZ. Saves roughly 64 USD per month in non-production."
  type        = bool
  default     = true
}