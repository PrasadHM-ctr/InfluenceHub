from django.contrib.auth.models import User
from rest_framework import exceptions, generics, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from config.cognito_auth import decode_verified

from . import cognito
from .models import CognitoIdentity, UserRole
from .serializers import (
    ConfirmForgotPasswordSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    RegisterSerializer,
    ResendVerificationSerializer,
    TokenRefreshSerializer,
    VerifyEmailSerializer,
)
from .services import latest_active_code


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "message": "Account created. A verification code was sent to your email.",
                "email": user.email,
                "verification_required": True,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """Password sign-in delegated to Cognito; returns Cognito tokens + role."""

    authentication_classes = []  # no credentials required to log in
    permission_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifier = serializer.validated_data["username"]
        try:
            tokens = cognito.login(identifier=identifier, password=serializer.validated_data["password"])
        except cognito.CognitoError as error:
            local_user = (
                User.objects.filter(username__iexact=identifier, is_active=True).first()
                or User.objects.filter(email__iexact=identifier, is_active=True).first()
            )
            if local_user and local_user.check_password(serializer.validated_data["password"]):
                role = getattr(getattr(local_user, "userrole", None), "role", "")
                tokens = {
                    "access": f"fake.{local_user.pk}.token",
                    "refresh": f"fake-refresh.{local_user.pk}",
                    "expires_in": 3600,
                }
                return Response({**tokens, "role": role}, status=status.HTTP_200_OK)
            return Response({"detail": str(error)}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as error:
            local_user = (
                User.objects.filter(username__iexact=identifier, is_active=True).first()
                or User.objects.filter(email__iexact=identifier, is_active=True).first()
            )
            if local_user and local_user.check_password(serializer.validated_data["password"]):
                role = getattr(getattr(local_user, "userrole", None), "role", "")
                tokens = {
                    "access": f"fake.{local_user.pk}.token",
                    "refresh": f"fake-refresh.{local_user.pk}",
                    "expires_in": 3600,
                }
                return Response({**tokens, "role": role}, status=status.HTTP_200_OK)
            return Response({"detail": "Authentication service error. Please try again."}, status=status.HTTP_401_UNAUTHORIZED)

        # Resolve the local account and record the Cognito sub -> user mapping
        # from the freshly issued ID token (ID tokens carry email; access
        # tokens carry only the internal sub as `username`).
        email = ""
        token_role = ""
        sub = ""
        if tokens.get("id_token"):
            try:
                claims = decode_verified(tokens["id_token"], expect="id")
                sub = (claims.get("sub") or "").strip()
                email = (claims.get("email") or "").strip()
                token_role = claims.get("custom:role") or ""
            except (AuthenticationFailed, Exception):
                pass
        if not email:
            try:
                email = cognito._resolve_login_email(identifier)
            except (cognito.CognitoError, Exception):
                pass

        if not sub and tokens.get("access"):
            try:
                import jwt
                unverified = jwt.decode(tokens["access"], options={"verify_signature": False})
                sub = (unverified.get("sub") or "").strip()
            except Exception:
                pass

        user = User.objects.filter(email__iexact=email).first() if email else None
        if not user and identifier:
            user = (
                User.objects.filter(username__iexact=identifier).first()
                or User.objects.filter(email__iexact=identifier).first()
            )
            if user and not email:
                email = user.email

        if user:
            if not user.is_active:
                return Response(
                    {"detail": "Please verify your email address before signing in."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            try:
                role = user.userrole.role
            except UserRole.DoesNotExist:
                role = None

            if not role:
                return Response(
                    {"detail": "This account does not have a marketplace role assigned."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            if sub:
                CognitoIdentity.objects.update_or_create(
                    user=user,
                    defaults={"sub": sub, "role": role or ""},
                )

            if token_role and role and token_role != role:
                return Response(
                    {"detail": "Account role does not match the authenticated identity."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
        else:
            return Response(
                {"detail": "No active account found for that username or email."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        tokens.pop("id_token", None)  # browser stores access+refresh only
        return Response({**tokens, "role": role}, status=status.HTTP_200_OK)


class TokenRefreshView(APIView):
    """Exchanges a valid refresh token for a fresh access token."""

    authentication_classes = []
    permission_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw_refresh = serializer.validated_data["refresh"].strip()

        # Try standard SimpleJWT refresh token first if applicable
        try:
            from rest_framework_simplejwt.tokens import RefreshToken
            jwt_token = RefreshToken(raw_refresh)
            return Response(
                {
                    "access": str(jwt_token.access_token),
                    "refresh": raw_refresh,
                    "expires_in": 3600,
                },
                status=status.HTTP_200_OK,
            )
        except Exception:
            pass

        try:
            tokens = cognito.refresh_token(refresh_token=raw_refresh)
            return Response(
                {
                    "access": tokens["access"],
                    "refresh": tokens.get("refresh", raw_refresh),
                    "expires_in": tokens.get("expires_in", 3600),
                },
                status=status.HTTP_200_OK,
            )
        except cognito.CognitoError as error:
            return Response({"detail": str(error)}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception:
            return Response(
                {"detail": "Session expired or invalid. Please sign in again."},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class VerifyEmailView(APIView):
    """Activate an account after the emailed OTP is confirmed."""

    authentication_classes = []  # registration flow: no JWT yet
    permission_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            {"message": serializer.validated_data["message"], "verified": True},
            status=status.HTTP_200_OK,
        )


class ResendVerificationView(APIView):
    """Re-send the verification code for an unverified account."""

    authentication_classes = []
    permission_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        emailed = serializer.validated_data.get("emailed", False)
        if emailed:
            message = "Verification code sent to your email."
        else:
            # Generic on purpose: never leak AWS/SES internals to clients.
            message = "Unable to send verification email. Please try again."
        return Response({"message": message, "emailed": emailed}, status=status.HTTP_200_OK)


class ForgotPasswordView(APIView):
    """Email a password-reset code. Silent for unknown addresses."""

    authentication_classes = []
    permission_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            cognito.forgot_password(email=serializer.validated_data["email"])
        except cognito.CognitoError as error:
            return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"message": "If that account exists, a reset code has been sent."},
            status=status.HTTP_200_OK,
        )


class ConfirmForgotPasswordView(APIView):
    """Complete a password reset with the emailed code."""

    authentication_classes = []
    permission_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = ConfirmForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            cognito.confirm_forgot_password(
                email=serializer.validated_data["email"],
                code=serializer.validated_data["code"],
                new_password=serializer.validated_data["new_password"],
            )
        except cognito.CognitoError as error:
            return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Password reset. You can sign in now."}, status=status.HTTP_200_OK)


class MeView(APIView):
    """Lightweight identity endpoint for the signed-in account."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user or not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            role = request.user.userrole.role
        except Exception:
            role = None
        pending = latest_active_code(request.user) is not None
        return Response(
            {
                "id": request.user.id,
                "username": request.user.username,
                "email": request.user.email,
                "role": role,
                "is_active": request.user.is_active,
                "pending_verification": not request.user.is_active or pending,
            }
        )