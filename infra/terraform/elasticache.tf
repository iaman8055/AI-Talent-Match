resource "aws_elasticache_subnet_group" "main" {
  name       = "ai-talent-match-${var.environment}"
  subnet_ids = aws_subnet.private[*].id
}

# Single-node cluster (no replication group) — sufficient for a Celery broker/cache at this
# scale; move to a replication group with automatic failover once traffic justifies it.
resource "aws_elasticache_cluster" "main" {
  cluster_id         = "ai-talent-match-${var.environment}"
  engine             = "redis"
  engine_version     = "7.1"
  node_type          = var.redis_node_type
  num_cache_nodes    = 1
  port               = 6379
  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]
  apply_immediately  = var.environment != "production"
}
