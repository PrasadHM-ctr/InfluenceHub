from rest_framework import serializers
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

from config.validators import validate_image_upload

from .models import InfluencerProfile
from accounts.models import UserRole
from accounts import cognito
from accounts.services import issue_verification_code


class InfluencerRegisterSerializer(serializers.Serializer):
    # User
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    # Influencer
    full_name = serializers.CharField(max_length=200)
    bio = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField(max_length=100)
    language = serializers.CharField(max_length=100)
    followers = serializers.IntegerField()

    instagram = serializers.URLField(required=False, allow_blank=True)
    youtube = serializers.URLField(required=False, allow_blank=True)
    facebook = serializers.URLField(required=False, allow_blank=True)

    city = serializers.CharField(max_length=100)
    state = serializers.CharField(max_length=100)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "Username already exists."
            )
        return value

    def validate_email(self, value):
        normalized = value.strip().lower()  # store normalized - case-insensitive identity
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError(
                "Email already exists."
            )
        return normalized

    @transaction.atomic
    def create(self, validated_data):

        # Account stays inactive until the emailed code is confirmed.
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            is_active=False,
        )
        # Cognito owns credentials from here on - PostgreSQL keeps no usable
        # password, so a database leak can never expose a login.
        user.set_unusable_password()
        user.save(update_fields=["password"])

        UserRole.objects.create(
            user=user,
            role="influencer",
        )

        influencer = InfluencerProfile.objects.create(
            user=user,
            full_name=validated_data["full_name"],
            bio=validated_data.get("bio", ""),
            category=validated_data["category"],
            language=validated_data["language"],
            followers=validated_data["followers"],
            instagram=validated_data.get("instagram", ""),
            youtube=validated_data.get("youtube", ""),
            facebook=validated_data.get("facebook", ""),
            city=validated_data["city"],
            state=validated_data["state"],
        )

        try:
            cognito.sign_up(
                email=user.email,
                password=validated_data["password"],
                role="influencer",
            )
        except cognito.CognitoError as error:
            # Rolls back the whole signup (user/role/profile) via atomic block.
            raise serializers.ValidationError(str(error)) from error

        return influencer


def influencer_completion(profile: InfluencerProfile) -> tuple[int, list[str]]:
    """Return (percentage, missing field labels) for a creator profile."""
    checks = [
        ("full_name", "Full name"),
        ("bio", "Bio"),
        ("category", "Category"),
        ("language", "Language"),
        ("city", "City"),
        ("state", "State"),
        ("instagram", "Instagram"),
        ("youtube", "YouTube"),
        ("profile_image", "Profile image"),
    ]
    missing = [label for attr, label in checks if not getattr(profile, attr)]
    complete = len(checks) - len(missing)
    return round((complete / len(checks)) * 100), missing


class InfluencerProfileSerializer(serializers.ModelSerializer):
    completion_percentage = serializers.SerializerMethodField()
    missing_fields = serializers.SerializerMethodField()
    portfolio = serializers.SerializerMethodField()
    is_verified = serializers.BooleanField(read_only=True)
    verification_status = serializers.CharField(read_only=True)
    email_verified = serializers.BooleanField(read_only=True)
    social_verification_code = serializers.CharField(read_only=True)
    verification_submitted_at = serializers.DateTimeField(read_only=True)
    verification_reviewed_at = serializers.DateTimeField(read_only=True)
    verification_rejection_reason = serializers.CharField(read_only=True)

    class Meta:
        model = InfluencerProfile
        fields = [
            "id",
            "full_name",
            "bio",
            "category",
            "language",
            "followers",
            "instagram",
            "youtube",
            "facebook",
            "city",
            "state",
            "profile_image",
            "completion_percentage",
            "missing_fields",
            "email_verified",
            "is_verified",
            "verification_status",
            "social_verification_code",
            "verification_submitted_at",
            "verification_reviewed_at",
            "verification_rejection_reason",
            "portfolio",
        ]
        read_only_fields = [
            "id",
            "email_verified",
            "is_verified",
            "verification_status",
            "social_verification_code",
            "verification_submitted_at",
            "verification_reviewed_at",
            "verification_rejection_reason",
        ]

    def get_portfolio(self, obj) -> list[str]:
        """Return list of portfolio media image URLs for the influencer."""
        try:
            from .portfolio_serializers import InfluencerMediaSerializer
            media = getattr(obj, "media", None)
            if media is None:
                return []
            serializer = InfluencerMediaSerializer(media.all(), many=True, context=getattr(self, "context", {}))
            return [item["image_url"] for item in serializer.data if item.get("image_url")]
        except Exception:
            return []

    def get_completion_percentage(self, obj) -> int:
        return influencer_completion(obj)[0]

    def get_missing_fields(self, obj) -> list[str]:
        return influencer_completion(obj)[1]

    def validate_profile_image(self, value):
        try:
            validate_image_upload(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages)
        return value


class InfluencerListSerializer(serializers.ModelSerializer):
    is_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = InfluencerProfile
        fields = [
            "id",
            "full_name",
            "category",
            "language",
            "followers",
            "city",
            "state",
            "instagram",
            "profile_image",
            "is_verified",
        ]


class VerificationRequestSerializer(serializers.Serializer):
    """Start the social-account ownership workflow.

    A code is generated that the influencer adds to their Instagram bio.
    An admin then confirms ownership manually — an Instagram URL alone never
    proves account ownership.
    """

    instagram_url = serializers.URLField()

    def validate_instagram_url(self, value):
        if "instagram.com" not in value.lower():
            raise serializers.ValidationError("Provide your Instagram profile URL.")
        return value