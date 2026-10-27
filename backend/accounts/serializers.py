from django.contrib.auth.models import User
from rest_framework import serializers

from . import cognito
from .models import UserRole


class LoginSerializer(serializers.Serializer):
    """Accepts the account username OR email plus its Cognito password."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class RegisterSerializer(serializers.ModelSerializer):
    """Create the local account AND the Cognito identity (inactive until the
    emailed OTP is confirmed via /api/verify-email/)."""

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def validate_email(self, value):
        # Product intent: emails are case-insensitively unique, so store them
        # normalized once ("Test@Gmail.com" and "test@gmail.com" are one
        # identity). Affects new registrations only - existing rows untouched.
        normalized = value.strip().lower()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("Email already exists.")
        return normalized

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            is_active=False,
        )
        # Cognito owns credentials - keep no usable password in PostgreSQL.
        user.set_unusable_password()
        user.save(update_fields=["password"])
        try:
            cognito.sign_up(
                email=user.email,
                password=validated_data["password"],
                role="influencer",
            )
        except cognito.CognitoError as error:
            raise serializers.ValidationError(str(error)) from error
        return user


class VerifyEmailSerializer(serializers.Serializer):
    """Confirm the Cognito-emailed OTP and activate the local account."""

    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)

    def validate(self, attrs):
        user = User.objects.filter(email__iexact=attrs["email"]).first()
        if not user:
            raise serializers.ValidationError({"email": "No account found for this email address."})
        if user.is_active:
            raise serializers.ValidationError({"email": "This account is already verified. Please sign in."})

        try:
            cognito.confirm_sign_up(email=attrs["email"], code=attrs["code"])
        except cognito.CognitoError as error:
            raise serializers.ValidationError({"code": str(error)}) from error

        user.is_active = True
        user.save(update_fields=["is_active"])
        if hasattr(user, "influencerprofile"):
            profile = user.influencerprofile
            if not profile.email_verified:
                profile.email_verified = True
                profile.save(update_fields=["email_verified"])

        attrs["user"] = user
        attrs["message"] = "Your email address has been verified. You can sign in now."
        return attrs


class ResendVerificationSerializer(serializers.Serializer):
    """Ask Cognito to re-email the verification code."""

    email = serializers.EmailField()

    def validate(self, attrs):
        user = User.objects.filter(email__iexact=attrs["email"], is_active=False).first()
        # Do not reveal whether the address exists (account-enumeration guard).
        if user:
            try:
                cognito.resend_confirmation_code(email=attrs["email"])
                attrs["emailed"] = True
            except cognito.CognitoError:
                attrs["emailed"] = False
        else:
            attrs["emailed"] = False
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ConfirmForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)
    new_password = serializers.CharField(write_only=True, min_length=8)


class TokenRefreshSerializer(serializers.Serializer):
    """Accepts a refresh token to generate a fresh access token."""

    refresh = serializers.CharField(required=True)

