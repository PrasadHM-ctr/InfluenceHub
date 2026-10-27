"""Database models for the owner-only administration panel."""

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Immutable record of privileged owner/admin actions.

    Stores who performed an action, on which target, and when. Only
    non-sensitive metadata is ever stored here - never passwords, OTP
    codes or cloud credentials.
    """

    ACTION_CHOICES = [
        ("admin_login", "Admin login"),
        ("user_viewed", "User viewed"),
        ("user_approved", "User approved"),
        ("user_rejected", "User rejected"),
        ("user_suspended", "User suspended"),
        ("user_activated", "User activated"),
        ("user_deleted", "User deleted"),
        ("campaign_viewed", "Campaign viewed"),
        ("campaign_cancelled", "Campaign cancelled by admin"),
        ("alerts_seen", "Admin alerts marked seen"),
    ]

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,  # log survives even if the actor is deleted
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=40, choices=ACTION_CHOICES)
    target_type = models.CharField(max_length=40, blank=True)  # e.g. "user"
    target_id = models.CharField(max_length=64, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action", "-created_at"], name="audit_action_idx"),
        ]

    def __str__(self):
        actor = self.actor.username if self.actor else "system"
        return f"{actor} {self.action} {self.target_type}:{self.target_id}"


class AdminAlertState(models.Model):
    """Singleton row remembering when the owner last reviewed the
    attention feed so unread counts can be computed from real data."""

    last_read_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Alert state (last read: {self.last_read_at})"
