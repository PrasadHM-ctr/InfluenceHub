from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from .models import Conversation, Message
from .services import mark_messages_read, notify_new_message, serialize_message


PRESENCE_TIMEOUT_SECONDS = 90


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """Authenticated real-time events for one accepted campaign conversation."""

    async def connect(self):
        self.connected = False
        self.conversation_id = int(self.scope["url_route"]["kwargs"]["conversation_id"])
        self.conversation = await self._get_conversation()
        if not self.conversation:
            await self.close(code=4403)
            return

        self.group_name = f"chat_{self.conversation_id}"
        self.other_user_id = self._other_user_id()
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        self.connected = True
        await self.accept()

        became_online = await self._mark_online(self.scope["user"].id)
        await self.send_json(
            {
                "type": "online_status",
                "user_id": self.other_user_id,
                "is_online": await self._is_online(self.other_user_id),
            }
        )
        if became_online:
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "chat.presence",
                    "user_id": self.scope["user"].id,
                    "is_online": True,
                },
            )

    async def disconnect(self, close_code):
        if not self.connected:
            return
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        became_offline = await self._mark_offline(self.scope["user"].id)
        if became_offline:
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "chat.presence",
                    "user_id": self.scope["user"].id,
                    "is_online": False,
                },
            )

    async def receive_json(self, content, **kwargs):
        event_type = content.get("type")

        if event_type == "message":
            await self._create_text_message(content.get("text", ""))
        elif event_type == "typing":
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "chat.typing",
                    "user_id": self.scope["user"].id,
                    "is_typing": bool(content.get("is_typing")),
                },
            )
        elif event_type == "read":
            raw_ids = content.get("message_ids", [])
            message_ids = [message_id for message_id in raw_ids[:100] if isinstance(message_id, int)] if isinstance(raw_ids, list) else []
            read_ids = await self._mark_messages_read(message_ids)
            if read_ids:
                await self.channel_layer.group_send(
                    self.group_name,
                    {"type": "chat.read_receipt", "message_ids": read_ids},
                )
        elif event_type == "presence_ping":
            await self._refresh_presence(self.scope["user"].id)
        else:
            await self.send_json({"type": "error", "detail": "Unsupported chat event."})

    async def chat_message(self, event):
        await self.send_json({"type": "message", "message": event["message"]})

    async def chat_typing(self, event):
        if event["user_id"] != self.scope["user"].id:
            await self.send_json(
                {
                    "type": "typing",
                    "user_id": event["user_id"],
                    "is_typing": event["is_typing"],
                }
            )

    async def chat_read_receipt(self, event):
        await self.send_json({"type": "read_receipt", "message_ids": event["message_ids"]})

    async def chat_presence(self, event):
        if event["user_id"] != self.scope["user"].id:
            await self.send_json(
                {
                    "type": "online_status",
                    "user_id": event["user_id"],
                    "is_online": event["is_online"],
                }
            )

    async def _create_text_message(self, text):
        if not isinstance(text, str) or not text.strip():
            await self.send_json({"type": "error", "detail": "A message cannot be empty."})
            return
        if len(text) > 4000:
            await self.send_json({"type": "error", "detail": "Messages are limited to 4,000 characters."})
            return

        message = await self._save_text_message(text.strip())
        await self._notify_other_party(message["id"])
        await self.channel_layer.group_send(
            self.group_name,
            {"type": "chat.message", "message": message},
        )

    @database_sync_to_async
    def _notify_other_party(self, message_id):
        try:
            message = Message.objects.select_related(
                "conversation",
                "conversation__business",
                "conversation__influencer",
                "conversation__business__user",
                "conversation__influencer__user",
                "sender",
            ).get(id=message_id)
        except Message.DoesNotExist:
            return
        notify_new_message(message)

    def _other_user_id(self):
        if self.conversation.business.user_id == self.scope["user"].id:
            return self.conversation.influencer.user_id
        return self.conversation.business.user_id

    @database_sync_to_async
    def _get_conversation(self):
        user = self.scope["user"]
        if not user or not user.is_authenticated:
            return None
        return (
            Conversation.objects.select_related("business", "influencer", "campaign")
            .filter(id=self.conversation_id, campaign__status="Accepted")
            .filter(
                Q(business__user=user) | Q(influencer__user=user)
            )
            .first()
        )

    @database_sync_to_async
    def _save_text_message(self, text):
        message = Message.objects.create(
            conversation_id=self.conversation_id,
            sender=self.scope["user"],
            text=text,
        )
        Conversation.objects.filter(id=self.conversation_id).update(updated_at=timezone.now())
        message = Message.objects.select_related(
            "sender",
            "sender__businessprofile",
            "sender__influencerprofile",
            "sender__userrole",
        ).get(id=message.id)
        return serialize_message(message)

    @database_sync_to_async
    def _mark_messages_read(self, message_ids):
        return mark_messages_read(
            conversation=self.conversation,
            user=self.scope["user"],
            message_ids=message_ids or None,
        )

    @staticmethod
    def _presence_key(user_id):
        return f"chat:presence:{user_id}"

    @staticmethod
    @sync_to_async
    def _mark_online(user_id):
        key = ChatConsumer._presence_key(user_id)
        count = cache.get(key, 0)
        cache.set(key, count + 1, timeout=PRESENCE_TIMEOUT_SECONDS)
        return count == 0

    @staticmethod
    @sync_to_async
    def _mark_offline(user_id):
        key = ChatConsumer._presence_key(user_id)
        count = cache.get(key, 0)
        if count <= 1:
            cache.delete(key)
            return count > 0
        cache.set(key, count - 1, timeout=PRESENCE_TIMEOUT_SECONDS)
        return False

    @staticmethod
    @sync_to_async
    def _refresh_presence(user_id):
        key = ChatConsumer._presence_key(user_id)
        count = cache.get(key, 0)
        if count:
            cache.set(key, count, timeout=PRESENCE_TIMEOUT_SECONDS)

    @staticmethod
    @sync_to_async
    def _is_online(user_id):
        return bool(cache.get(ChatConsumer._presence_key(user_id), 0))
