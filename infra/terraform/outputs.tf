output "api_alb_dns_name" {
  description = "Public DNS name of the API's load balancer. Point var.api_public_url (and a real custom domain, once one exists) at this."
  value       = aws_lb.api.dns_name
}

output "web_alb_dns_name" {
  description = "Public DNS name of the web app's load balancer."
  value       = aws_lb.web.dns_name
}

output "rds_endpoint" {
  description = "RDS Postgres connection endpoint (host:port)."
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache Redis connection endpoint (host)."
  value       = aws_elasticache_cluster.main.cache_nodes[0].address
  sensitive   = true
}

output "resumes_bucket_name" {
  description = "S3 bucket name for resume storage (if used instead of/alongside Supabase Storage)."
  value       = aws_s3_bucket.resumes.bucket
}

output "app_secret_arn" {
  description = "Secrets Manager secret ARN holding the app's runtime env vars."
  value       = aws_secretsmanager_secret.app.arn
}
