from rest_framework import serializers
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

from config.validators import validate_image_upload

from .models import BusinessProfile
from accounts.models import UserRole
from accounts import cognito


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
        normalized = value.strip().lower()  # store normalized - case-insensitive identity
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError(
                "Email already exists."
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
        user.set_unusable_password()
        user.save(update_fields=["password"])

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

        try:
            cognito.sign_up(
                email=user.email,
                password=validated_data["password"],
                role="business",
            )
        except cognito.CognitoError as error:
            # Rolls back the whole signup (user/role/profile) via atomic block.
            raise serializers.ValidationError(str(error)) from error

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