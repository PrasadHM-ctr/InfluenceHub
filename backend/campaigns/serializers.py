from rest_framework import serializers
from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.exceptions import ObjectDoesNotExist

from config.validators import validate_document_upload, validate_image_upload

from .models import CampaignRequest


def _attachment_url(file_field, request=None):
    if not file_field:
        return None
    if request:
        return request.build_absolute_uri(file_field.url)
    return f"{settings.BACKEND_PUBLIC_URL.rstrip('/')}{file_field.url}"


class CampaignSerializer(serializers.ModelSerializer):
    business_name = serializers.ReadOnlyField(source="business.company_name")
    influencer_name = serializers.ReadOnlyField(source="influencer.full_name")
    conversation_id = serializers.SerializerMethodField()
    attachment_url = serializers.SerializerMethodField()

    def get_conversation_id(self, obj):
        try:
            return obj.conversation.id
        except ObjectDoesNotExist:
            return None

    def get_attachment_url(self, obj):
        return _attachment_url(obj.attachment, self.context.get("request"))

    class Meta:
        model = CampaignRequest
        fields = [
            "id",
            "business",
            "business_name",
            "influencer",
            "influencer_name",
            "conversation_id",
            "title",
            "message",
            "budget",
            "status",
            "attachment",
            "attachment_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["business", "business_name", "influencer_name", "conversation_id", "status", "created_at", "updated_at"]

    def validate_attachment(self, value):
        if not value:
            return value
        try:
            # Campaign briefs may be an image or a PDF document.
            content_type = getattr(value, "content_type", "") or ""
            if content_type.startswith("image/"):
                validate_image_upload(value)
            else:
                validate_document_upload(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages)
        return value