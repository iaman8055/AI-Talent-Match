# Resume storage. Note: current app config (core/config.py's supabase_s3_* settings) points at
# Supabase Storage's S3-compatible API, not this bucket — this is the AWS-native equivalent for
# when/if storage moves off Supabase. Wire SUPABASE_S3_ENDPOINT_URL et al. to this bucket's
# endpoint (or keep using Supabase Storage and skip this resource entirely) — either is a valid
# choice, this file just makes the AWS option available.

resource "aws_s3_bucket" "resumes" {
  bucket = "ai-talent-match-${var.environment}-resumes"
}

resource "aws_s3_bucket_public_access_block" "resumes" {
  bucket = aws_s3_bucket.resumes.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "resumes" {
  bucket = aws_s3_bucket.resumes.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "resumes" {
  bucket = aws_s3_bucket.resumes.id
  versioning_configuration {
    status = "Enabled"
  }
}
