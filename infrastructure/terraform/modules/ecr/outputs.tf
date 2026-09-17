output "repository_urls" {
  description = "Push and pull URLs per service"
  value       = { for k, v in aws_ecr_repository.main : k => v.repository_url }
}

output "repository_arns" {
  value = { for k, v in aws_ecr_repository.main : k => v.arn }
}