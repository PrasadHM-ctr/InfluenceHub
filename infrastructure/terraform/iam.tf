# =============================================================================
# InfluenceHub — application IAM (least privilege)
#
# The Django app may ONLY:
#   * Put / Get / Delete objects INSIDE the one media bucket
#   * Send transactional email via SES
#
# It can NOT:
#   * create or destroy AWS infrastructure (no iam:*, no cloudformation, …)
#   * touch any other bucket, service or account resource
#   * administer SES identities
#
# NO access keys are generated here — secrets must never land in Terraform
# state. After applying, create the key yourself and store it in backend/.env:
#
#   aws iam create-access-key --user-name <iam_user_name>
#
# =============================================================================

resource "aws_iam_user" "app" {
  name = var.iam_user_name

  tags = merge(local.common_tags, {
    Purpose = "influencehub-app-runtime"
  })
}

data "aws_iam_policy_document" "app" {
  # Bucket-level listing. Required: without s3:ListBucket, S3 answers
  # HeadObject with 403 (not 404) for missing keys, which breaks
  # django-storages' exists()/overwrite checks.
  statement {
    sid       = "MediaBucketList"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = ["arn:aws:s3:::${var.s3_bucket_name}"]
  }

  # Media objects inside the single bucket.
  statement {
    sid       = "MediaObjectsReadWriteDelete"
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["arn:aws:s3:::${var.s3_bucket_name}/*"]
  }

  # HeadObject (used by django-storages exists()/overwrite checks) maps to
  # s3:GetObject, which the statement above already grants — so no
  # ListBucket is needed. Least privilege wins.

  dynamic "statement" {
    for_each = var.create_ses_identity && var.ses_from_email != "" ? [1] : []
    content {
      sid       = "SendTransactionalEmail"
      effect    = "Allow"
      actions   = ["ses:SendEmail", "ses:SendRawEmail"]
      resources = [aws_ses_email_identity.from[0].arn]
    }
  }

  dynamic "statement" {
    for_each = !(var.create_ses_identity && var.ses_from_email != "") ? [1] : []
    content {
      sid       = "SendTransactionalEmailAnyIdentity"
      effect    = "Allow"
      actions   = ["ses:SendEmail", "ses:SendRawEmail"]
      resources = ["*"] # Identity created outside Terraform; still Send-only.
    }
  }

  # Cognito authentication actions the Django backend performs on behalf of
  # signups/logins. Strictly scoped to THIS user pool; no pool administration.
  dynamic "statement" {
    for_each = var.create_cognito ? [1] : []
    content {
      sid    = "CognitoAuthFlowsOnly"
      effect = "Allow"
      actions = [
        "cognito-idp:SignUp",
        "cognito-idp:ConfirmSignUp",
        "cognito-idp:ResendConfirmationCode",
        "cognito-idp:InitiateAuth",
        "cognito-idp:ForgotPassword",
        "cognito-idp:ConfirmForgotPassword",
      ]
      resources = [aws_cognito_user_pool.main.arn]
    }
  }

  # Owner-panel moderation: permanently deleting an application account must
  # also remove its authentication record, otherwise the email can never be
  # registered again ("An account with the given email already exists").
  # AdminGetUser/ListUsers are read-only diagnostics used to detect stale
  # identities. Still strictly scoped to THIS single user pool.
  dynamic "statement" {
    for_each = var.create_cognito ? [1] : []
    content {
      sid    = "CognitoAccountLifecycle"
      effect = "Allow"
      actions = [
        "cognito-idp:AdminDeleteUser",
        "cognito-idp:AdminGetUser",
        "cognito-idp:ListUsers",
      ]
      resources = [aws_cognito_user_pool.main.arn]
    }
  }
}

resource "aws_iam_user_policy" "app" {
  name   = "${var.project_name}-app-least-privilege"
  user   = aws_iam_user.app.name
  policy = data.aws_iam_policy_document.app.json
}
