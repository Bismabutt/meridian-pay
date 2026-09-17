output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "Public subnet IDs, for load balancers"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet IDs, for nodes and databases"
  value       = aws_subnet.private[*].id
}

output "nat_gateway_ips" {
  description = "NAT public IPs. Partners may need these allowlisted."
  value       = aws_eip.nat[*].public_ip
}