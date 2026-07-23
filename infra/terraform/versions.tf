# Written to match docs/02-ARCHITECTURE.md §6's stated deployment target (ECS Fargate + RDS +
# ElastiCache + S3, Qdrant Cloud/NVIDIA as external managed services). Not `init`'d or `apply`'d
# as part of this session — there's no AWS account wired here, and provisioning real
# infrastructure/spend is a call for whoever operates this to make deliberately, not something
# to trigger implicitly. No remote state backend is configured yet; add one (S3 + DynamoDB lock
# table) before the first real `apply` so state isn't only ever local.

terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "ai-talent-match"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
