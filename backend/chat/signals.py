from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from campaigns.models import CampaignRequest

from .models import Conversation, Message


@receiver(post_save, sender=CampaignRequest)
def create_conversation_for_accepted_campaign(sender, instance, **kwargs):
    if instance.status == "Accepted":
        Conversation.objects.get_or_create(
            campaign=instance,
            defaults={"business": instance.business, "influencer": instance.influencer},
        )


@receiver(post_save, sender=Message)
def update_conversation_timestamp(sender, instance, **kwargs):
    Conversation.objects.filter(id=instance.conversation_id).update(updated_at=timezone.now())
