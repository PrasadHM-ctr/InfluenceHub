# =============================================================================
# InfluenceHub — Amazon SES identity (transactional email only)
#
# Scope: verification codes and their resends — nothing else. No marketing,
# bulk, newsletter or scheduled sending exists anywhere in the codebase.
#
# Notes:
#   * New SES accounts start in the SANDBOX: you can only send to verified
#     addresses until AWS approves a production-access request. That is fine
#     for development (verify your own test addresses).
#   * SES has a Free Tier allowance that varies by account/region — verify
#     current pricing yourself; this stack never guarantees $0.
#   * Set create_ses_identity=false if you prefer plain SMTP credentials.
# =============================================================================

resource "aws_ses_email_identity" "from" {
  count = var.create_ses_identity && var.ses_from_email != "" ? 1 : 0

  email = var.ses_from_email
}
