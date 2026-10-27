from django.contrib.auth.models import User
from django.db import models


class Notification(models.Model):
    TYPE_CHOICES = [
        ("campaign_new", "New campaign"),
        ("campaign_accepted", "Campaign accepted"),
        ("campaign_rejected", "Campaign rejected"),
        ("campaign_completed", "Campaign completed"),
        ("campaign_cancelled", "Campaign cancelled"),
        ("message_new", "New message"),
        ("verification", "Profile verification"),
    ]

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "-created_at"], name="notif_recipient_idx"),
            models.Index(fields=["recipient", "is_read"], name="notif_recipient_read_idx"),
        ]

    def __str__(self):
        return f"{self.notification_type} → {self.recipient.username}"
