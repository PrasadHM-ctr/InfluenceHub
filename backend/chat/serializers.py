from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from campaigns.models import CampaignRequest
from config.validators import validate_chat_file_upload

from .models import Conversation, Message


def _file_url(file_field, request=None):
    if not file_field:
        return None
    if request:
        return request.build_absolute_uri(file_field.url)
    return f"{settings.BACKEND_PUBLIC_URL.rstrip('/')}{file_field.url}"


class MessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.IntegerField(source="sender.id", read_only=True)
    sender_name = serializers.SerializerMethodField()
    sender_role = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "conversation",
            "sender_id",
            "sender_name",
            "sender_role",
            "text",
            "image_url",
            "file_url",
            "is_read",
            "created_at",
        ]

    def get_sender_name(self, obj):
        if hasattr(obj.sender, "businessprofile"):
            return obj.sender.businessprofile.company_name
        if hasattr(obj.sender, "influencerprofile"):
            return obj.sender.influencerprofile.full_name
        return obj.sender.username

    def get_sender_role(self, obj):
        try:
            return obj.sender.userrole.role
        except AttributeError:
            return None

    def get_image_url(self, obj):
        return _file_url(obj.image, self.context.get("request"))

    def get_file_url(self, obj):
        return _file_url(obj.file, self.context.get("request"))


class ConversationSerializer(serializers.ModelSerializer):
    campaign_id = serializers.IntegerField(source="campaign.id", read_only=True)
    campaign_title = serializers.CharField(source="campaign.title", read_only=True)
    campaign_budget = serializers.DecimalField(source="campaign.budget", max_digits=10, decimal_places=2, read_only=True)
    other_party = serializers.SerializerMethodField()
    latest_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "campaign_id",
            "campaign_title",
            "campaign_budget",
            "other_party",
            "latest_message",
            "unread_count",
            "created_at",
            "updated_at",
        ]

    def get_other_party(self, obj):
        request = self.context["request"]
        if obj.business.user_id == request.user.id:
            return {
                "id": obj.influencer_id,
                "name": obj.influencer.full_name,
                "role": "influencer",
                "image_url": _file_url(obj.influencer.profile_image, request),
            }
        return {
            "id": obj.business_id,
            "name": obj.business.company_name,
            "role": "business",
            "image_url": _file_url(obj.business.logo, request),
        }

    def get_latest_message(self, obj):
        messages = getattr(obj, "latest_messages", [])
        if not messages:
            return None
        return MessageSerializer(messages[0], context=self.context).data

    def get_unread_count(self, obj):
        return getattr(obj, "unread_count", 0)


class StartConversationSerializer(serializers.Serializer):
    campaign_id = serializers.PrimaryKeyRelatedField(
        queryset=CampaignRequest.objects.select_related("business", "influencer"),
        source="campaign",
    )


class UploadMessageSerializer(serializers.Serializer):
    conversation = serializers.PrimaryKeyRelatedField(queryset=Conversation.objects.all())
    image = serializers.ImageField(required=False)
    file = serializers.FileField(required=False)

    def validate(self, attrs):
        image = attrs.get("image")
        uploaded_file = attrs.get("file")
        if not image and not uploaded_file:
            raise serializers.ValidationError("Choose an image or file to upload.")
        if image and uploaded_file:
            raise serializers.ValidationError("Upload one image or file at a time.")

        candidate = image or uploaded_file
        try:
            validate_chat_file_upload(candidate, image=image is not None)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages)
        return attrs
