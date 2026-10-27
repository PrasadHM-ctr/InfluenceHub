from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class UserRole(models.Model):
    ROLE_CHOICES = [
        ("business", "Business"),
        ("influencer", "Influencer"),
        # Explicit platform-owner role. NEVER offered during public signup;
        # assigned only via `python manage.py create_owner`.
        ("owner", "Owner"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES
    )

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class EmailVerificationCode(models.Model):
    """Single-use email OTP issued during registration (legacy local flow).

    Kept so no historical data is lost; Cognito now delivers the codes.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="email_verification_codes",
    )
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="accounts_email_code_idx"),
        ]

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_consumed(self) -> bool:
        return self.consumed_at is not None

    @property
    def ttl_minutes(self) -> int:
        return settings.EMAIL_VERIFICATION_CODE_TTL_MINUTES

    def __str__(self):
        return f"Verification code for {self.user.username}"


class CognitoIdentity(models.Model):
    """Links a Cognito user (by its immutable `sub`) to the local account.

    Cognito access tokens carry only the internal sub as `username`, so this
    mapping — written at every successful login from the verified ID token —
    is how protected requests resolve to a Django user.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="cognito_identity",
    )
    sub = models.CharField(max_length=64, unique=True, db_index=True)
    role = models.CharField(max_length=20, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.sub} -> {self.user.username}"