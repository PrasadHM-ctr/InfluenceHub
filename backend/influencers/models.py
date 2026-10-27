from django.conf import settings
from django.db import models
from django.contrib.auth.models import User


class InfluencerProfile(models.Model):
    VERIFICATION_STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    full_name = models.CharField(max_length=200)

    bio = models.TextField(blank=True)

    category = models.CharField(max_length=100)

    language = models.CharField(max_length=100)

    followers = models.IntegerField(default=0)

    instagram = models.URLField(blank=True)

    youtube = models.URLField(blank=True)

    facebook = models.URLField(blank=True)

    city = models.CharField(max_length=100)

    state = models.CharField(max_length=100)

    profile_image = models.ImageField(
        upload_to="profiles/",
        blank=True,
        null=True
    )

    # --- Trust & authenticity -------------------------------------------------
    email_verified = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        default="Pending",
    )
    # Code the influencer adds to their Instagram bio so an admin can confirm
    # ownership of the linked account. A URL alone never proves ownership.
    social_verification_code = models.CharField(max_length=32, blank=True)

    # --- Verification audit shortcuts (full trail lives in VerificationAudit) -
    verification_submitted_at = models.DateTimeField(null=True, blank=True)
    verification_reviewed_at = models.DateTimeField(null=True, blank=True)
    verification_rejection_reason = models.TextField(blank=True, default="")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="influencer_verifications_reviewed",
    )

    def __str__(self):
        return self.full_name
from django.conf import settings  # noqa: F401  (appended block)


# ==========================================================================
# Portfolio media + verification audit trail (owner-panel upgrade)
# ==========================================================================
class InfluencerMedia(models.Model):
    """Portfolio / promotional image uploaded by an influencer (stored in S3)."""

    influencer = models.ForeignKey(
        InfluencerProfile,
        on_delete=models.CASCADE,
        related_name="media",
    )
    image = models.ImageField(upload_to="profiles/portfolio/%Y/%m/")
    caption = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Influencer media"
        verbose_name_plural = "Influencer media"

    def __str__(self):
        return f"Portfolio media #{self.pk} of {self.influencer}"

    def delete(self, *args, **kwargs):
        """Remove the stored file so the media bucket is not littered with orphans."""
        try:
            from config.media_cleanup import delete_replaced_file

            if self.image:
                delete_replaced_file(self.image)
        except Exception:
            pass
        super().delete(*args, **kwargs)


class VerificationAudit(models.Model):
    """Immutable audit trail of the influencer verification workflow."""

    ACTION_SUBMITTED = "SUBMITTED"
    ACTION_APPROVED = "APPROVED"
    ACTION_REJECTED = "REJECTED"

    ACTION_CHOICES = (
        (ACTION_SUBMITTED, "Submitted for review"),
        (ACTION_APPROVED, "Approved"),
        (ACTION_REJECTED, "Rejected"),
    )

    profile = models.ForeignKey(
        InfluencerProfile,
        on_delete=models.CASCADE,
        related_name="verification_audits",
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    reason = models.TextField(blank=True, default="")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verification_reviews_given",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Verification audit"
        verbose_name_plural = "Verification audits"

    def __str__(self):
        return f"{self.action} - {self.profile} @ {self.created_at:%Y-%m-%d %H:%M}"

