output "cluster_name" {
  value = aws_eks_cluster.main.name
}

output "cluster_endpoint" {
  description = "Kubernetes API endpoint"
  value       = aws_eks_cluster.main.endpoint
}

output "cluster_certificate_authority" {
  description = "CA data for kubeconfig"
  value       = aws_eks_cluster.main.certificate_authority[0].data
  sensitive   = true
}

output "cluster_security_group_id" {
  value = aws_eks_cluster.main.vpc_config[0].cluster_security_group_id
}

output "oidc_provider_arn" {
  description = "For IRSA role trust policies"
  value       = aws_iam_openid_connect_provider.cluster.arn
}

output "oidc_provider_url" {
  value = replace(aws_iam_openid_connect_provider.cluster.url, "https://", "")
}

output "node_role_arn" {
  value = aws_iam_role.node.arn
}

output "kubeconfig_command" {
  description = "Run this to configure kubectl"
  value       = "aws eks update-kubeconfig --region eu-west-2 --name ${aws_eks_cluster.main.name}"
}