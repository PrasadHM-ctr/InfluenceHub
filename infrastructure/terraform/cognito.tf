# =============================================================================
# InfluenceHub - Amazon Cognito User Pool (authentication)
#
# ONE pool serves BOTH roles. The role lives in the custom:role attribute
# ("business" | "influencer") set at signup and re-validated by Django from
# the verified JWT - the frontend role is never trusted alone.
#
# Email delivery uses Cognito's built-in verifier (COGNITO_DEFAULT), which
# sends OTPs from AWS's shared sender and is NOT subject to the SES sandbox,
# so real Gmail addresses receive codes immediately.
# =============================================================================

resource "aws_cognito_user_pool" "main" {
  name = "${var.project_name}-users"

  # Users register AND sign in with their email address.
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  mfa_configuration = "OFF"

  password_policy {
    minimum_length                   = 8
    require_lowercase                = false
    require_numbers                  = false
    require_symbols                  = false
    require_uppercase                = false
    temporary_password_validity_days = 7
  }

  # Verification + password-reset codes are delivered by EMAIL ONLY.
  # No SMS/SNS configuration exists in this stack by design.
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
    email_subject        = "Your InfluenceHub verification code"
    email_message        = <<-EOT
      Welcome to InfluenceHub!

      Your verification code is {####}

      Enter this code in InfluenceHub to activate your account. It expires soon and can be used only once.

      Security warning: never share this code - the InfluenceHub team will never ask you for it.
    EOT
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # Role carried inside signed tokens so Django can cross-check the DB role.
  schema {
    name                = "role"
    attribute_data_type = "String"
    mutable             = true

    string_attribute_constraints {
      min_length = 1
      max_length = 32
    }
  }

  tags = merge(local.common_tags, {
    Purpose = "influencehub-authentication"
  })
}

resource "aws_cognito_user_pool_client" "app" {
  name         = "${var.project_name}-backend"
  user_pool_id = aws_cognito_user_pool.main.id

  # The PASSWORD grant is called by the DJANGO BACKEND (server -> AWS), never
  # directly from the browser - the browser only ever talks to Django.
  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]

  prevent_user_existence_errors = "ENABLED"

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }

  access_token_validity  = 1
  id_token_validity      = 1
  refresh_token_validity = 30
}

