# =============================================================================
# InfluenceHub — outputs
#
# Use these values in backend/.env (never commit that file).
# =============================================================================

output "s3_bucket_name" {
  description = "Media bucket to set as AWS_STORAGE_BUCKET_NAME."
  value       = aws_s3_bucket.media.id
}

output "aws_region" {
  description = "Region for AWS_S3_REGION_NAME / AWS_SES_REGION_NAME."
  value       = var.aws_region
}

output "ses_identity_arn" {
  description = "ARN of the SES identity used for verification emails (null when disabled)."
  value       = try(aws_ses_email_identity.from[0].arn, null)
}

output "iam_user_name" {
  description = "Application user. Create its access key manually — never commit it:"
  value       = aws_iam_user.app.name
}

output "cognito_user_pool_id" {
  description = "Set as COGNITO_USER_POOL_ID in backend/.env."
  value       = var.create_cognito ? aws_cognito_user_pool.main.id : null
}

output "cognito_app_client_id" {
  description = "Set as COGNITO_APP_CLIENT_ID in backend/.env (public value, not a secret)."
  value       = var.create_cognito ? aws_cognito_user_pool_client.app.id : null
}

output "next_steps" {
  description = "What to do after a reviewed `terraform plan` + apply."
  value = join("\n", [
    "1) terraform apply was NOT run automatically - review the plan first.",
    "2) Verify the SES email address in the AWS console (sandbox mode).",
    "3) Create app credentials WITHOUT Terraform so secrets stay out of state:",
    "     aws iam create-access-key --user-name ${var.iam_user_name}",
    "4) Put the key into backend/.env (USE_S3=true, USE_SES=true) and never commit it.",
    "5) Check billing weekly: https://console.aws.amazon.com/billing/",
  ])
}
