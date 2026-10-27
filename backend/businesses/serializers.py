from rest_framework import serializers
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

from config.validators import validate_image_upload

from .models import BusinessProfile
from accounts.models import UserRole
import logging
from accounts import cognito
from accounts.services import issue_verification_code

logger = logging.getLogger(__name__)


class BusinessRegisterSerializer(serializers.Serializer):
    # User fields
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    # Business fields
    company_name = serializers.CharField(max_length=200)
    industry = serializers.CharField(max_length=100)
    website = serializers.URLField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20)
    city = serializers.CharField(max_length=100)
    state = serializers.CharField(max_length=100)

    # Validation
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "Username already exists."
            )
        return value

    def validate_email(self, value):
        normalized = value.strip().lower()
        existing = User.objects.filter(email__iexact=normalized).first()
        if existing:
            if existing.is_active:
                raise serializers.ValidationError("An account with this email already exists. Please sign in.")
            raise serializers.ValidationError(
                "An unverified account with this email already exists. Please check your inbox or click Resend code."
            )
        return normalized

    # Create Business Account
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

        # Save Role
        UserRole.objects.create(
            user=user,
            role="business",
        )
        # Save Business Profile
        business = BusinessProfile.objects.create(
            user=user,
            company_name=validated_data["company_name"],
            industry=validated_data["industry"],
            website=validated_data.get("website", ""),
            description=validated_data.get("description", ""),
            phone=validated_data["phone"],
            city=validated_data["city"],
            state=validated_data["state"],
        )

        cognito_ok = False
        try:
            cognito.sign_up(
                email=user.email,
                password=validated_data["password"],
                role="business",
            )
            cognito_ok = True
        except cognito.CognitoError as error:
            logger.info("Cognito sign_up note: %s", error)

        code_obj, sent = issue_verification_code(user=user)
        self.context["email_sent"] = sent or cognito_ok
        self.context["verification_code"] = code_obj.code

        return business


def business_completion(profile: BusinessProfile) -> tuple[int, list[str]]:
    """Return (percentage, missing field labels) for a business profile."""
    checks = [
        ("company_name", "Company name"),
        ("industry", "Industry"),
        ("website", "Website"),
        ("description", "Description"),
        ("phone", "Phone"),
        ("city", "City"),
        ("state", "State"),
        ("logo", "Business logo"),
    ]
    missing = [label for attr, label in checks if not getattr(profile, attr)]
    complete = len(checks) - len(missing)
    return round((complete / len(checks)) * 100), missing


class BusinessProfileSerializer(serializers.ModelSerializer):
    completion_percentage = serializers.SerializerMethodField()
    missing_fields = serializers.SerializerMethodField()

    class Meta:
        model = BusinessProfile
        fields = [
            "company_name",
            "industry",
            "website",
            "description",
            "phone",
            "city",
            "state",
            "logo",
            "completion_percentage",
            "missing_fields",
        ]

    def get_completion_percentage(self, obj) -> int:
        return business_completion(obj)[0]

    def get_missing_fields(self, obj) -> list[str]:
        return business_completion(obj)[1]

    def validate_logo(self, value):
        try:
            validate_image_upload(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages)
        return value