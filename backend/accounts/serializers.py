from django.contrib.auth.models import User
from rest_framework import serializers

from . import cognito
import logging
from django.utils import timezone
from .models import UserRole, EmailVerificationCode
from .services import issue_verification_code, confirm_email_with_code

logger = logging.getLogger(__name__)


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
        normalized = value.strip().lower()
        existing = User.objects.filter(email__iexact=normalized).first()
        if existing:
            if existing.is_active:
                raise serializers.ValidationError("An account with this email already exists. Please sign in.")
            raise serializers.ValidationError(
                "An unverified account with this email already exists. Please check your inbox or click Resend code."
            )
        return normalized

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            is_active=False,
        )
        # Cognito owns credentials - keep no usable password in PostgreSQL.
        cognito_ok = False
        try:
            cognito.sign_up(
                email=user.email,
                password=validated_data["password"],
                role="influencer",
            )
            cognito_ok = True
        except cognito.CognitoError as error:
            logger.info("Cognito sign_up note: %s", error)

        code_obj, sent = issue_verification_code(user=user)
        self.context["email_sent"] = sent or cognito_ok
        self.context["verification_code"] = code_obj.code
        return user


class VerifyEmailSerializer(serializers.Serializer):
    """Confirm the Cognito-emailed OTP and activate the local account."""

    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)

    def validate(self, attrs):
        email_normalized = attrs["email"].strip().lower()
        code_str = attrs["code"].strip()
        user = User.objects.filter(email__iexact=email_normalized).first()
        if not user:
            raise serializers.ValidationError({"email": "No account found for this email address."})
        if user.is_active:
            raise serializers.ValidationError({"email": "This account is already verified. Please sign in."})

        # 1. Try local EmailVerificationCode first
        local_ok, local_msg = confirm_email_with_code(user=user, code=code_str)

        # 2. Try Cognito confirmation
        cognito_ok = False
        try:
            cognito.confirm_sign_up(email=email_normalized, code=code_str)
            cognito_ok = True
        except Exception:
            pass

        if not local_ok and not cognito_ok:
            is_expired = EmailVerificationCode.objects.filter(
                user=user, code=code_str, expires_at__lte=timezone.now()
            ).exists()
            if is_expired:
                raise serializers.ValidationError({"code": "This code has expired. Request a new one."})
            raise serializers.ValidationError({"code": "That verification code is not correct."})

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
        email_normalized = attrs["email"].strip().lower()
        user = User.objects.filter(email__iexact=email_normalized, is_active=False).first()
        if not user:
            attrs["emailed"] = False
            attrs["message"] = "If an unverified account exists for this email, a code was sent."
            return attrs

        from django.conf import settings
        cooldown = getattr(settings, "EMAIL_RESEND_COOLDOWN_SECONDS", 30)
        if cooldown > 0:
            recent = EmailVerificationCode.objects.filter(
                user=user,
                created_at__gte=timezone.now() - timezone.timedelta(seconds=cooldown),
            ).first()
            if recent:
                raise serializers.ValidationError({"email": f"Please wait {cooldown} seconds before requesting another code."})

        code_obj, sent = issue_verification_code(user=user)
        cognito_ok = False
        try:
            cognito.resend_confirmation_code(email=user.email)
            cognito_ok = True
        except Exception:
            pass

        attrs["emailed"] = sent or cognito_ok
        attrs["message"] = (
            "Verification code sent to your email."
            if (sent or cognito_ok)
            else "Unable to send verification email. Please try again."
        )
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

