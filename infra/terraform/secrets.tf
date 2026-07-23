# Real secrets (docs/02-ARCHITECTURE.md §6: "AWS Secrets Manager, injected as ECS task
# environment — never .env in any deployed image"). Values come in via Terraform variables
# (TF_VAR_* env vars / a real secrets pipeline in CI), never hardcoded here.

locals {
  database_url = "postgresql+psycopg://${var.db_username}:${var.db_password}@${aws_db_instance.main.endpoint}/${var.db_name}"
  redis_url    = "redis://${aws_elasticache_cluster.main.cache_nodes[0].address}:6379/0"
}

resource "aws_secretsmanager_secret" "app" {
  name = "ai-talent-match/${var.environment}/app"
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    DATABASE_URL    = local.database_url
    REDIS_URL       = local.redis_url
    JWT_SECRET_KEY  = var.jwt_secret_key
    QDRANT_URL      = var.qdrant_url
    QDRANT_API_KEY  = var.qdrant_api_key
    NVIDIA_API_KEY  = var.nvidia_api_key
    FRONTEND_URL    = var.frontend_url
    SENTRY_DSN      = var.sentry_dsn
  })
}
