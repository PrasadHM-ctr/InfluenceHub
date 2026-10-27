"""Email verification helpers.

Codes are delivered through Django's configured email backend. In development
the console backend prints the message (including the code) to the runserver
terminal; in production set SMTP_* environment variables to deliver real mail.
"""

import logging
import secrets

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.utils.html import escape
from django.utils import timezone

from .models import EmailVerificationCode

logger = logging.getLogger(__name__)

CODE_LENGTH = 6


def generate_code() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(CODE_LENGTH))


def issue_verification_code(*, user: User) -> tuple[EmailVerificationCode, bool]:
    """Create a fresh single-use code and email it to the user.

    Any previous outstanding code for the user is invalidated first, so only
    the newest OTP can activate the account.

    Returns (code, sent) — `sent` is False when the email could not be
    delivered (e.g. SES sandbox recipient not yet verified).
    """
    ttl_minutes = settings.EMAIL_VERIFICATION_CODE_TTL_MINUTES
    # Retire older codes: after a Resend, only the freshly issued OTP is valid.
    EmailVerificationCode.objects.filter(
        user=user, consumed_at__isnull=True
    ).update(consumed_at=timezone.now())
    code = EmailVerificationCode.objects.create(
        user=user,
        code=generate_code(),
        expires_at=timezone.now() + timezone.timedelta(minutes=ttl_minutes),
    )
    sent = _send_code_email(user, code)
    return code, sent


def latest_active_code(user: User) -> EmailVerificationCode | None:
    return (
        EmailVerificationCode.objects.filter(
            user=user,
            consumed_at__isnull=True,
            expires_at__gt=timezone.now(),
        )
        .order_by("-created_at")
        .first()
    )


def confirm_email_with_code(*, user: User, code: str) -> tuple[bool, str]:
    """Validate an OTP and activate the account. Returns (ok, message)."""
    verification = (
        EmailVerificationCode.objects.filter(user=user, code=code.strip())
        .order_by("-created_at")
        .first()
    )
    if not verification:
        return False, "That code is not valid for this account."
    if verification.is_consumed:
        return False, "This code has already been used."
    if verification.is_expired:
        return False, "This code has expired. Request a new one."

    verification.consumed_at = timezone.now()
    verification.save(update_fields=["consumed_at"])

    user.is_active = True
    user.save(update_fields=["is_active"])

    # Keep the influencer profile flag in sync when applicable.
    if hasattr(user, "influencerprofile"):
        profile = user.influencerprofile
        if not profile.email_verified:
            profile.email_verified = True
            profile.save(update_fields=["email_verified"])

    return True, "Your email address has been verified. You can sign in now."


def _verification_code_html(*, username: str, code: str, ttl_minutes: int) -> str:
    """Branded HTML alternative for the OTP email (no external assets)."""
    return (
        '<!DOCTYPE html><html><body style="margin:0;padding:24px;'
        'background:#f8fafc;font-family:Arial,Helvetica,sans-serif;">'
        '<div style="max-width:520px;margin:0 auto;background:#ffffff;border-radius:16px;'
        'border:1px solid #e2e8f0;padding:32px;text-align:center;">'
        '<div style="font-size:20px;font-weight:bold;color:#7c3aed;">InfluenceHub</div>'
        '<h1 style="font-size:22px;color:#0f172a;margin:12px 0;">Email Verification</h1>'
        f'<p style="color:#334155;font-size:15px;line-height:1.6;">Hi {escape(username)},</p>'
        '<p style="color:#334155;font-size:15px;line-height:1.6;">'
        'Use the verification code below to activate your account:</p>'
        f'<div style="font-size:34px;letter-spacing:10px;font-weight:bold;color:#0f172a;'
        f'background:#f1f5f9;border-radius:12px;padding:16px;margin:20px 0;">{escape(code)}</div>'
        f'<p style="color:#64748b;font-size:13px;">This code expires in {int(ttl_minutes)} minutes '
        'and can be used only once.</p>'
        '<p style="color:#94a3b8;font-size:12px;line-height:1.6;">'
        'Security warning: never share this code &mdash; the InfluenceHub team will never ask '
        'for it. If you did not create this account, you can safely ignore this email.</p>'
        '</div></body></html>'
    )


def _send_code_email(user: User, verification: EmailVerificationCode) -> bool:
    """Deliver the OTP as multipart/alternative (plain text + HTML).

    Returns True only when the configured backend actually accepted the
    message (e.g. SES ``SendEmail`` succeeded, console printed it). A False
    return means delivery failed — callers must not claim an email is on its
    way. Failures are logged server-side; no AWS internals reach the client.
    """
    subject = "Your InfluenceHub verification code"
    body = (
        f"Hi {user.username},\n\n"
        "InfluenceHub — Email Verification\n\n"
        f"Welcome to InfluenceHub! Use the verification code below to activate "
        f"your account:\n\n"
        f"    {verification.code}\n\n"
        f"This code expires in {verification.ttl_minutes} minutes and can be "
        f"used only once.\n\n"
        "Security warning: never share this code — the InfluenceHub team will "
        "never ask you for it. If you did not create this account you can "
        "safely ignore this email.\n\n"
        "— The InfluenceHub team"
    )
    try:
        sent = send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=_verification_code_html(
                username=user.username,
                code=verification.code,
                ttl_minutes=verification.ttl_minutes,
            ),
            fail_silently=False,
        )
        if not sent:
            logger.warning(
                "Verification email to %s returned 0 messages sent", user.email
            )
        return bool(sent)
    except Exception:  # pragma: no cover - delivery issues must not break signup
        logger.exception("Failed to send verification email to %s", user.email)
        return False
