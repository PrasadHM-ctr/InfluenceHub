from django.conf import settings
from django.db.models import Count, Max, Prefetch, Q
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Conversation, Message
from .serializers import (
    ConversationSerializer,
    MessageSerializer,
    StartConversationSerializer,
    UploadMessageSerializer,
)
from .services import (
    broadcast_message,
    broadcast_read_receipt,
    mark_messages_read,
    notify_new_message,
    require_conversation_access,
    start_conversation,
    touch_conversation,
)


class ConversationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        unread_filter = Q(messages__is_read=False) & ~Q(messages__sender=request.user)
        conversations = (
            Conversation.objects.filter(campaign__status="Accepted")
            .filter(Q(business__user=request.user) | Q(influencer__user=request.user))
            .select_related("business", "influencer", "campaign")
            .annotate(unread_count=Count("messages", filter=unread_filter), last_message_at=Max("messages__created_at"))
            .prefetch_related(
                Prefetch(
                    "messages",
                    queryset=Message.objects.select_related(
                        "sender",
                        "sender__businessprofile",
                        "sender__influencerprofile",
                        "sender__userrole",
                    ).order_by("-id")[:1],
                    to_attr="latest_messages",
                )
            )
            .order_by("-last_message_at", "-updated_at")
        )
        return Response(ConversationSerializer(conversations, many=True, context={"request": request}).data)


class ConversationMessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        conversation = require_conversation_access(user=request.user, conversation_id=conversation_id)
        try:
            limit = min(max(int(request.query_params.get("limit", 40)), 1), 100)
            before = request.query_params.get("before")
            before_id = int(before) if before else None
        except ValueError:
            return Response({"detail": "Invalid pagination parameters."}, status=status.HTTP_400_BAD_REQUEST)

        messages = Message.objects.filter(conversation=conversation).select_related(
            "sender",
            "sender__businessprofile",
            "sender__influencerprofile",
            "sender__userrole",
        ).order_by("-id")
        if before_id:
            messages = messages.filter(id__lt=before_id)

        page = list(messages[: limit + 1])
        has_more = len(page) > limit
        page = list(reversed(page[:limit]))

        read_ids = mark_messages_read(conversation=conversation, user=request.user)
        broadcast_read_receipt(conversation.id, read_ids)
        return Response(
            {
                "messages": MessageSerializer(page, many=True, context={"request": request}).data,
                "has_more": has_more,
            }
        )


class StartConversationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = StartConversationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation, created = start_conversation(user=request.user, campaign=serializer.validated_data["campaign"])
        return Response(
            ConversationSerializer(conversation, context={"request": request}).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class UploadMessageView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = UploadMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation = require_conversation_access(
            user=request.user,
            conversation_id=serializer.validated_data["conversation"].id,
        )

        # Cost guard: keep stored attachments per conversation bounded so a
        # single chat can never grow S3 storage without limit.
        cap = settings.CHAT_MAX_ATTACHMENTS_PER_CONVERSATION
        if cap and (
            Message.objects.filter(conversation=conversation)
            .filter(Q(image__isnull=False) | Q(file__isnull=False))
            .count()
            >= cap
        ):
            return Response(
                {"detail": "This conversation has reached its attachment limit."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            image=serializer.validated_data.get("image"),
            file=serializer.validated_data.get("file"),
        )
        touch_conversation(conversation.id)
        notify_new_message(message)
        broadcast_message(message, request)
        return Response(MessageSerializer(message, context={"request": request}).data, status=status.HTTP_201_CREATED)


class UnreadCountView(APIView):
    """Total unread messages across every conversation of the caller."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        unread = Message.objects.filter(is_read=False).filter(
            Q(conversation__business__user=request.user) | Q(conversation__influencer__user=request.user)
        ).exclude(sender=request.user).count()
        return Response({"unread_count": unread})
