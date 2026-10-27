from django.db import models
from businesses.models import BusinessProfile
from influencers.models import InfluencerProfile


class CampaignRequest(models.Model):

    STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("Accepted", "Accepted"),
        ("Rejected", "Rejected"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
    )

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="campaigns_sent",
    )

    influencer = models.ForeignKey(
        InfluencerProfile,
        on_delete=models.CASCADE,
        related_name="campaigns_received",
    )

    title = models.CharField(max_length=200)

    message = models.TextField()

    budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending",
    )

    # Optional campaign brief / media file (images or PDF) stored in S3 or
    # local media; PostgreSQL keeps only the reference.
    attachment = models.FileField(
        upload_to="campaigns/%Y/%m/",
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.business.company_name} -> {self.influencer.full_name}"