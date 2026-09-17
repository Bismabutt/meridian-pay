output "database_endpoints" {
  description = "Connection endpoints per service"
  value       = { for k, v in aws_db_instance.main : k => v.address }
}

output "database_security_group_id" {
  value = aws_security_group.database.id
}

output "secret_arns" {
  description = "Secrets Manager ARNs holding each database's credentials"
  value       = { for k, v in aws_secretsmanager_secret.db : k => v.arn }
}

output "secret_names" {
  value = { for k, v in aws_secretsmanager_secret.db : k => v.name }
}