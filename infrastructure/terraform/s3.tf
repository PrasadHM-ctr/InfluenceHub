# =============================================================================
# InfluenceHub — the ONE media bucket
#
# Cost posture (Free-Tier friendly):
#   * exactly one bucket for every upload (profiles/, business_logos/,
#     campaigns/, chat/)
#   * fully PRIVATE: Block Public Access (all four) + BucketOwnerEnforced
#     (ACLs disabled) — objects are read by the Django backend only
#   * SSE-S3 server-side encryption (no KMS key charges)
#   * versioning OFF by default (overwrites would otherwise double storage)
#   * NO Intelligent-Tiering, Analytics, Inventory, replication,
#     transfer acceleration or lifecycle transitions to other classes
#   * the ONLY lifecycle rule aborts incomplete multipart uploads after 7
#     days so failed uploads never bill silently forever
#
# Image display flows through Django URLs; the browser never writes here.
# =============================================================================

resource "aws_s3_bucket" "media" {
  bucket = var.s3_bucket_name

  tags = local.common_tags
}

# Block every form of public exposure. This is non-negotiable.
resource "aws_s3_bucket_public_access_block" "media" {
  bucket = aws_s3_bucket.media.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Disable ACLs entirely; access is governed solely by IAM.
resource "aws_s3_bucket_ownership_controls" "media" {
  bucket = aws_s3_bucket.media.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }

  # Never create the bucket before public access is blocked.
  depends_on = [aws_s3_bucket_public_access_block.media]
}

# Server-side encryption with S3-managed keys (AES256) — free, no KMS costs.
resource "aws_s3_bucket_server_side_encryption_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = false
  }

  depends_on = [aws_s3_bucket_ownership_controls.media]
}

resource "aws_s3_bucket_versioning" "media" {
  bucket = aws_s3_bucket.media.id

  versioning_configuration {
    # Suspended == single current copy per object (lowest cost).
    status = var.enable_s3_versioning ? "Enabled" : "Suspended"
  }

  depends_on = [aws_s3_bucket_ownership_controls.media]
}

# Only lifecycle rule allowed: kill orphaned multipart uploads.
resource "aws_s3_bucket_lifecycle_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  depends_on = [aws_s3_bucket_versioning.media]
}

# Read-only CORS for local front-ends during development. GET only — the
# browser never uploads directly; all writes go through the Django API.
resource "aws_s3_bucket_cors_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  cors_rule {
    id              = "readonly-local-development"
    allowed_methods = ["GET"]
    allowed_headers = ["*"]
    allowed_origins = var.allowed_cors_origins
    expose_headers  = ["etag"]
    max_age_seconds = 3600
  }

  depends_on = [aws_s3_bucket_ownership_controls.media]
}
