# =============================================================================
# InfluenceHub — Terraform provider
#
# Credentials are NEVER written in these files. The provider uses the normal
# AWS credential chain (environment variables, `aws sso login`, or
# `aws configure` shared-credentials file).
#
#   export AWS_ACCESS_KEY_ID=...      # your admin/terraform user, NOT the app user
#   export AWS_SECRET_ACCESS_KEY=...
#
# =============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  # Refuse to run against a non-standard endpoint by accident.
  default_tags {
    tags = local.common_tags
  }
}
