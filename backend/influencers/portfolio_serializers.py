"""Serializers for influencer portfolio media and the verification audit trail."""

import os

from rest_framework import serializers

from .models import InfluencerMedia, VerificationAudit

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_SIZE_MB = 5


class InfluencerMediaSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = InfluencerMedia
        fields = ["id", "image", "image_url", "caption", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_image_url(self, obj):
        request = self.context.get("request")
        try:
            url = obj.image.url
        except (ValueError, AttributeError):
            return None
        if request is not None:
            return request.build_absolute_uri(url)
        return url


class InfluencerMediaCreateSerializer(InfluencerMediaSerializer):
    """Upload serializer — validates type and size before anything touches S3."""

    class Meta(InfluencerMediaSerializer.Meta):
        fields = ["image", "caption"]
        read_only_fields = []

    def validate_image(self, value):
        extension = os.path.splitext(getattr(value, "name", "") or "")[1].lower()
        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            raise serializers.ValidationError(
                "Only JPG, JPEG, PNG and WEBP images are allowed."
            )
        max_bytes = MAX_IMAGE_SIZE_MB * 1024 * 1024
        size = getattr(value, "size", 0) or 0
        if size > max_bytes:
            raise serializers.ValidationError(
                f"Image must be smaller than {MAX_IMAGE_SIZE_MB}MB."
            )
        return value


class VerificationAuditSerializer(serializers.ModelSerializer):
    reviewed_by_email = serializers.SerializerMethodField()

    class Meta:
        model = VerificationAudit
        fields = ["id", "action", "reason", "reviewed_by_email", "created_at"]

    def get_reviewed_by_email(self, obj):
        user = obj.reviewed_by
        return getattr(user, "email", None) if user else None
