# =============================================================================
# InfluenceHub — input variables
#
# Only Free-Tier-eligible services are provisioned by this stack:
#   * one private S3 bucket (media storage)
#   * one IAM user with least-privilege permissions
#   * an optional SES email identity (transactional email only)
#
# Nothing else: no EC2, RDS, NAT Gateway, ALB, CloudFront, Lambda,
# API Gateway, ECS/Fargate, EKS, ElastiCache or OpenSearch.
# =============================================================================

variable "aws_region" {
  description = "AWS region for all resources. Keep every resource in ONE region to avoid inter-region data-transfer costs."
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Project tag applied to every resource."
  type        = string
  default     = "influencehub"
}

variable "s3_bucket_name" {
  description = "Globally unique name of the SINGLE media bucket (lowercase, no spaces)."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", var.s3_bucket_name))
    error_message = "Bucket name must be lowercase alphanumeric/dots/hyphens, 3-63 characters."
  }
}

variable "enable_s3_versioning" {
  description = "Versioning doubles stored bytes when files are overwritten. Keep false unless explicitly required."
  type        = bool
  default     = false
}

variable "allowed_cors_origins" {
  description = "Origins allowed to GET media objects cross-origin. Read-only; never enables writes from the browser."
  type        = list(string)
  default = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
  ]
}

variable "create_ses_identity" {
  description = "Create the SES email identity for transactional verification emails. Set false if you send through plain SMTP instead."
  type        = bool
  default     = true
}

variable "ses_from_email" {
  description = "Verified sender address for verification emails (e.g. no-reply@yourdomain.com). Leave empty to skip identity creation."
  type        = string
  default     = ""
}

variable "iam_user_name" {
  description = "Name of the application IAM user (least-privilege S3 + SES only)."
  type        = string
  default     = "influencehub-app"
}

variable "create_cognito" {
  description = "Create the Cognito User Pool used for signup / email verification / login."
  type        = bool
  default     = true
}
