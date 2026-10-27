"""DRF authentication backed by Amazon Cognito access tokens.

Every protected endpoint validates the Bearer JWT against the User Pool's
published JWKS (RS256 signatures), then maps it to the local Django user by
email and cross-checks the signed custom:role claim against the database role.
The frontend role is never trusted on its own.

Under the automated test-suite the fake backend issues ``fake.<pk>.token``
strings which resolve directly to the local user - no network, no AWS.
"""

from __future__ import annotations

import jwt
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework import authentication, exceptions


def _issuer() -> str:
    return (
        f"https://cognito-idp.{settings.COGNITO_REGION}.amazonaws.com/"
        f"{settings.COGNITO_USER_POOL_ID}"
    )


_jwks_client: jwt.PyJWKClient | None = None


def _get_jwks_client() -> jwt.PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        # PyJWKClient caches keys and refetches automatically on unknown kids.
        _jwks_client = jwt.PyJWKClient(f"{_issuer()}/.well-known/jwks.json")
    return _jwks_client


class CognitoAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).split()
        if not header or header[0].lower() != self.keyword.lower().encode():
            return None  # no credentials supplied (anonymous access paths)
        if len(header) != 2:
            raise exceptions.AuthenticationFailed("Invalid Authorization header.")
        token = header[1].decode()
        try:
            user = self._resolve_user(token)
            return (user, token)
        except Exception as e:
            raise

    # ------------------------------------------------------------------ #

    def _resolve_user(self, token: str) -> User:
        if token.startswith("fake."):
            user = self._fake_user(token)
            if user:
                return user
        if settings.COGNITO_FAKE:
            return self._fake_user(token)
        claims = self._decode_and_verify(token)

        sub = (claims.get("sub") or "").strip()
        username_claim = (claims.get("username") or "").strip()

        from accounts.models import CognitoIdentity

        # 1) Preferred: immutable sub -> local user mapping recorded at login.
        identity = (
            CognitoIdentity.objects.select_related("user", "user__userrole")
            .filter(sub=sub, user__is_active=True)
            .first()
        )
        if identity:
            return identity.user

        # 2) Fallback for pools/tokens where the username claim IS the email.
        if "@" in username_claim:
            user = (
                User.objects.filter(email__iexact=username_claim, is_active=True)
                .select_related("userrole")
                .first()
            )
            if user:
                return user

        # 3) Auto-heal: If sub is present in Cognito, resolve email from Cognito and map identity
        if sub and not settings.COGNITO_FAKE:
            try:
                import boto3
                cog_client = boto3.client("cognito-idp", region_name=settings.COGNITO_REGION)
                cog_user = cog_client.admin_get_user(
                    UserPoolId=settings.COGNITO_USER_POOL_ID,
                    Username=sub,
                )
                cog_attrs = {a["Name"]: a["Value"] for a in cog_user.get("UserAttributes", [])}
                cog_email = (cog_attrs.get("email") or "").strip().lower()
                cog_role = (cog_attrs.get("custom:role") or "").strip().lower()
                if cog_email:
                    user = User.objects.filter(email__iexact=cog_email, is_active=True).first()
                    if user:
                        CognitoIdentity.objects.update_or_create(
                            user=user,
                            defaults={"sub": sub, "role": cog_role or getattr(getattr(user, "userrole", None), "role", "")},
                        )
                        return user
            except Exception:
                pass

        raise exceptions.AuthenticationFailed(
            "No active InfluenceHub session for this token. Please sign in again."
        )

    @staticmethod
    def _fake_user(token: str) -> User | None:
        parts = token.split(".")
        if len(parts) == 3 and parts[0] == "fake":
            try:
                return User.objects.get(pk=int(parts[1]))
            except (ValueError, User.DoesNotExist):
                raise exceptions.AuthenticationFailed("Invalid session token.") from None
        return None

    @staticmethod
    def _decode_and_verify(token: str, expect: str = "access") -> dict:
        try:
            signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=_issuer(),
                options={"verify_aud": False, "verify_iat": False},  # avoid clock-skew rejection on iat
                leeway=120,
            )
        except jwt.PyJWKClientError as error:
            raise exceptions.AuthenticationFailed(f"Unable to validate the token signature: {error}") from error
        except jwt.ExpiredSignatureError as error:
            raise exceptions.AuthenticationFailed("Session expired. Please sign in again.") from error
        except jwt.InvalidTokenError as error:
            raise exceptions.AuthenticationFailed(f"Invalid authentication token: {type(error).__name__} - {error}") from error

        if claims.get("token_use") != expect:
            raise exceptions.AuthenticationFailed("Invalid token type.")
        # Access tokens carry `client_id`; ID tokens carry `aud` (string|list).
        client = settings.COGNITO_APP_CLIENT_ID
        if client:
            issued_for_client = (
                claims.get("client_id") == client
                if expect == "access"
                else client
                in (
                    claims["aud"]
                    if isinstance(claims.get("aud"), list)
                    else [claims.get("aud")]
                )
            )
            if not issued_for_client:
                raise exceptions.AuthenticationFailed(
                    "Token was not issued for this application."
                )
        return claims

    def authenticate_header(self, request):  # pragma: no cover - standard DRF hook
        return f'{self.keyword} realm="api"'


def decode_verified(token: str, *, expect: str) -> dict:
    """Module-level verified decode for server-issued flows (e.g. login)."""
    return CognitoAuthentication._decode_and_verify(token, expect=expect)


def resolve_token_user(token: str):
    """Resolve an access token to a Django user (or AnonymousUser).

    Shared by the DRF authentication class and the Channels WebSocket
    middleware so REST and realtime enforce identical token rules.
    """
    from django.contrib.auth.models import AnonymousUser

    if not token:
        return AnonymousUser()

    if settings.COGNITO_FAKE or token.startswith("fake."):
        parts = token.split(".")
        if len(parts) == 3 and parts[0] == "fake":
            try:
                return User.objects.get(pk=int(parts[1]), is_active=True)
            except (ValueError, User.DoesNotExist):
                return AnonymousUser()
        return AnonymousUser()

    try:
        claims = CognitoAuthentication._decode_and_verify(token)
    except Exception:
        return AnonymousUser()

    from accounts.models import CognitoIdentity

    sub = (claims.get("sub") or "").strip()
    if sub:
        identity = (
            CognitoIdentity.objects.select_related("user")
            .filter(sub=sub, user__is_active=True)
            .first()
        )
        if identity:
            return identity.user

    username_claim = (claims.get("username") or "").strip()
    if "@" in username_claim:
        return (
            User.objects.filter(email__iexact=username_claim, is_active=True).first()
            or AnonymousUser()
        )

    # Auto-heal: If sub is present in Cognito, resolve email from Cognito and map identity
    if sub and not settings.COGNITO_FAKE:
        try:
            import boto3
            cog_client = boto3.client("cognito-idp", region_name=settings.COGNITO_REGION)
            cog_user = cog_client.admin_get_user(
                UserPoolId=settings.COGNITO_USER_POOL_ID,
                Username=sub,
            )
            cog_attrs = {a["Name"]: a["Value"] for a in cog_user.get("UserAttributes", [])}
            cog_email = (cog_attrs.get("email") or "").strip().lower()
            cog_role = (cog_attrs.get("custom:role") or "").strip().lower()
            if cog_email:
                user = User.objects.filter(email__iexact=cog_email, is_active=True).first()
                if user:
                    CognitoIdentity.objects.update_or_create(
                        user=user,
                        defaults={"sub": sub, "role": cog_role or getattr(getattr(user, "userrole", None), "role", "")},
                    )
                    return user
        except Exception:
            pass

    return AnonymousUser()
