# =============================================================================
# InfluenceHub — shared locals
#
# COST CONTRACT: this stack provisions ONLY
#   * one private S3 bucket          (media storage)
#   * one IAM user + inline policy   (least-privilege app permissions)
#   * one optional SES email identity(transactional verification email)
#
# If a future `terraform plan` shows ANY other resource, STOP and review —
# never apply unexpected resources.
# =============================================================================

locals {
  common_tags = {
    Project     = var.project_name
    ManagedBy   = "terraform"
    CostProfile = "free-tier-only"
  }
}
