variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment name (e.g. staging, production) — used in resource names/tags."
  type        = string
  default     = "staging"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.20.0.0/16"
}

variable "availability_zones" {
  description = "Two AZs to spread subnets across."
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

# --- Container images (built + pushed to ECR by CI, referenced here by tag) ---

variable "api_image" {
  description = "Full ECR image URI:tag for the FastAPI app (infra/docker/Dockerfile.api)."
  type        = string
}

variable "worker_image" {
  description = "Full ECR image URI:tag for the Celery worker/beat (infra/docker/Dockerfile.worker)."
  type        = string
}

variable "web_image" {
  description = "Full ECR image URI:tag for the Next.js app (infra/docker/Dockerfile.web)."
  type        = string
}

# --- Database ---

variable "db_name" {
  description = "RDS Postgres database name."
  type        = string
  default     = "talent_match"
}

variable "db_username" {
  description = "RDS Postgres master username."
  type        = string
  default     = "talent_match"
}

variable "db_password" {
  description = "RDS Postgres master password. Pass via TF_VAR_db_password / a real secrets pipeline — never commit a value for this."
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  description = "RDS instance class — single-AZ db.t4g.micro is the docs/03-ROADMAP.md-stated acceptable baseline for early beta; move to Multi-AZ once there's paying usage (docs/02-ARCHITECTURE.md §6)."
  type        = string
  default     = "db.t4g.micro"
}

variable "db_multi_az" {
  description = "Whether RDS runs Multi-AZ. Off by default per the architecture doc's early-beta guidance."
  type        = bool
  default     = false
}

# --- Cache/broker ---

variable "redis_node_type" {
  description = "ElastiCache Redis node type."
  type        = string
  default     = "cache.t4g.micro"
}

# --- External managed services this Terraform does NOT provision ---

variable "qdrant_url" {
  description = "Qdrant Cloud cluster URL (external managed service, not provisioned here)."
  type        = string
}

variable "qdrant_api_key" {
  description = "Qdrant Cloud API key."
  type        = string
  sensitive   = true
}

variable "nvidia_api_key" {
  description = "NVIDIA hosted inference API key."
  type        = string
  sensitive   = true
}

variable "jwt_secret_key" {
  description = "JWT signing secret for the API."
  type        = string
  sensitive   = true
}

variable "frontend_url" {
  description = "Public URL of the deployed web app (used for CORS origin and email links)."
  type        = string
}

variable "api_public_url" {
  description = "Public URL the web app should call for the API (NEXT_PUBLIC_API_URL). Point this at api_alb_dns_name (or a real custom domain once one exists) after the first apply."
  type        = string
}

variable "api_cpu" {
  description = "Fargate task CPU units for the api service."
  type        = number
  default     = 512
}

variable "api_memory" {
  description = "Fargate task memory (MiB) for the api service."
  type        = number
  default     = 1024
}

variable "worker_cpu" {
  description = "Fargate task CPU units for the worker/beat services."
  type        = number
  default     = 512
}

variable "worker_memory" {
  description = "Fargate task memory (MiB) for the worker/beat services."
  type        = number
  default     = 1024
}

variable "web_cpu" {
  description = "Fargate task CPU units for the web service."
  type        = number
  default     = 256
}

variable "web_memory" {
  description = "Fargate task memory (MiB) for the web service."
  type        = number
  default     = 512
}

variable "sentry_dsn" {
  description = "Sentry DSN. Leave blank to run with Sentry disabled (matches core/sentry.py's no-op-when-unset behavior)."
  type        = string
  default     = ""
  sensitive   = true
}
