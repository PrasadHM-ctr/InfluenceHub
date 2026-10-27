from asgiref.sync import async_to_sync
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from channels.layers import get_channel_layer
from rest_framework.exceptions import PermissionDenied, ValidationError

from notifications.services import notify

from .models import Conversation, Message
from .serializers import MessageSerializer


def conversation_for_user(*, user, conversation_id):
    return (
        Conversation.objects.select_related("business", "influencer", "campaign")
        .filter(id=conversation_id, campaign__status="Accepted")
        .filter(Q(business__user=user) | Q(influencer__user=user))
        .first()
    )


def require_conversation_access(*, user, conversation_id):
    conversation = conversation_for_user(user=user, conversation_id=conversation_id)
    if not conversation:
        raise PermissionDenied("You do not have access to this conversation.")
    return conversation


def start_conversation(*, user, campaign):
    if campaign.status != "Accepted":
        raise ValidationError({"campaign_id": "Chat is available only after this campaign is accepted."})
    if user.id not in {campaign.business.user_id, campaign.influencer.user_id}:
        raise PermissionDenied("You do not have access to this campaign.")
    return Conversation.objects.get_or_create(
        campaign=campaign,
        defaults={"business": campaign.business, "influencer": campaign.influencer},
    )


@transaction.atomic
def mark_messages_read(*, conversation, user, message_ids=None):
    queryset = conversation.messages.filter(is_read=False).exclude(sender=user)
    if message_ids:
        queryset = queryset.filter(id__in=message_ids)
    message_ids = list(queryset.values_list("id", flat=True))
    if message_ids:
        queryset.update(is_read=True)
    return message_ids


def serialize_message(message, request=None):
    return MessageSerializer(message, context={"request": request}).data


def broadcast_to_conversation(conversation_id, event_type, payload):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"chat_{conversation_id}",
        {"type": event_type, **payload},
    )


def broadcast_message(message, request=None):
    broadcast_to_conversation(
        message.conversation_id,
        "chat.message",
        {"message": serialize_message(message, request)},
    )


def broadcast_read_receipt(conversation_id, message_ids):
    if message_ids:
        broadcast_to_conversation(
            conversation_id,
            "chat.read_receipt",
            {"message_ids": message_ids},
        )


def touch_conversation(conversation_id):
    Conversation.objects.filter(id=conversation_id).update(updated_at=timezone.now())


def notify_new_message(message: Message) -> None:
    """Notify the other participant about a new chat message."""
    conversation = message.conversation
    sender = message.sender
    recipient = (
        conversation.business.user
        if conversation.influencer.user_id == sender.id
        else conversation.influencer.user
    )
    if recipient is None or recipient.id == sender.id:
        return

    preview = (message.text or "").strip()
    if not preview:
        preview = "Sent you an attachment" if message.image else "Sent you a file"
    if len(preview) > 120:
        preview = f"{preview[:117]}…"

    try:
        sender_name = (
            sender.businessprofile.company_name
            if hasattr(sender, "businessprofile")
            else sender.influencerprofile.full_name
        )
    except Exception:
        sender_name = sender.username

    notify(
        recipient=recipient,
        notification_type="message_new",
        title="New message",
        message=f"{sender_name}: {preview}",
        link="/business/messages" if hasattr(recipient, "businessprofile") else "/influencer/messages",
    )
