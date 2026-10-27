from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models

from businesses.models import BusinessProfile
from campaigns.models import CampaignRequest
from influencers.models import InfluencerProfile


class Conversation(models.Model):
    """The single private chat created for an accepted campaign."""

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    influencer = models.ForeignKey(
        InfluencerProfile,
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    campaign = models.OneToOneField(
        CampaignRequest,
        on_delete=models.CASCADE,
        related_name="conversation",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["business", "-updated_at"], name="chat_conv_business_upd_idx"),
            models.Index(fields=["influencer", "-updated_at"], name="chat_conv_influencer_upd_idx"),
        ]

    def clean(self):
        if self.campaign_id and (
            self.campaign.business_id != self.business_id
            or self.campaign.influencer_id != self.influencer_id
        ):
            raise ValidationError("Conversation participants must match the campaign.")

    def __str__(self):
        return f"Conversation for campaign #{self.campaign_id}"


class Message(models.Model):
    """A text or single-file message in a private conversation."""

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )
    text = models.TextField(blank=True)
    image = models.ImageField(upload_to="chat/images/%Y/%m/%d/", blank=True, null=True)
    file = models.FileField(upload_to="chat/files/%Y/%m/%d/", blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["conversation", "-id"], name="chat_msg_conv_id_desc_idx"),
            models.Index(fields=["sender", "is_read"], name="chat_msg_sender_read_idx"),
        ]

    def clean(self):
        if not (self.text.strip() if self.text else "") and not self.image and not self.file:
            raise ValidationError("A message must contain text, an image, or a file.")
        if self.image and self.file:
            raise ValidationError("A message can contain either an image or a file, not both.")

    def __str__(self):
        return f"Message #{self.pk} in conversation #{self.conversation_id}"
