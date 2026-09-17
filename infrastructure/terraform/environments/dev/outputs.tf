output "vpc_id" {
  value = module.network.vpc_id
}

output "public_subnet_ids" {
  value = module.network.public_subnet_ids
}

output "private_subnet_ids" {
  value = module.network.private_subnet_ids
}

output "nat_gateway_ips" {
  description = "Outbound IPs. Partners may need these allowlisted."
  value       = module.network.nat_gateway_ips
}

output "cluster_name" {
  value = module.eks.cluster_name
}

output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "kubeconfig_command" {
  value = module.eks.kubeconfig_command
}

output "database_endpoints" {
  value = module.rds.database_endpoints
}

output "database_secret_names" {
  value = module.rds.secret_names
}

output "redis_endpoint" {
  value = module.redis.redis_endpoint
}

output "ecr_repository_urls" {
  value = module.ecr.repository_urls
}