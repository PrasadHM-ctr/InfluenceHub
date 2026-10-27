"""Amazon Cognito access layer (single point of contact with cognito-idp).

The Django backend performs ALL Cognito calls server-side; browsers never talk
to AWS directly and no credentials exist in frontend code.

Two interchangeable backends live here:

* ``real``  - boto3 calls against the User Pool from COGNITO_* env settings.
              Credentials come exclusively from the normal AWS chain (.env).
* ``fake``  - an in-process stand-in used by the automated test-suite (or when
              no pool is configured) so tests stay hermetic and never hit AWS.

The fake confirms signups with the fixed code ``123456`` and issues tokens of
the form ``fake.<user_pk>`` which config.cognito_auth understands.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import User


class CognitoError(Exception):
    """Raised for any Cognito rejection (message is safe to show users)."""

    def __init__(self, message: str, aws_code: str = ""):
        super().__init__(message)
        self.aws_code = aws_code


# ---------------------------------------------------------------------------
# helpers shared by both backends
# ---------------------------------------------------------------------------

def _resolve_login_email(identifier: str) -> str:
    """Login accepts a username OR an email; Cognito keys users by email."""
    if "@" in identifier:
        return identifier.strip().lower()
    user = (
        User.objects.filter(username__iexact=identifier.strip()).first()
        or User.objects.filter(email__iexact=identifier.strip()).first()
    )
    if not user or not user.email:
        raise CognitoError("No account found for that username.")
    return user.email.strip().lower()


def _tokens(result: dict) -> dict:
    auth = result.get("AuthenticationResult", {})
    if not auth.get("AccessToken"):
        raise CognitoError("Authentication failed.", "NotAuthorizedException")
    return {
        "access": auth["AccessToken"],
        "refresh": auth.get("RefreshToken", ""),
        "id_token": auth.get("IdToken", ""),
        "expires_in": auth.get("ExpiresIn", 3600),
    }


# ---------------------------------------------------------------------------
# fake backend (tests / pool-not-configured)
# ---------------------------------------------------------------------------

_FAKE_USERS: dict[str, dict] = {}
FAKE_CONFIRM_CODE = "123456"


def _fake_sign_up(email: str, password: str, role: str) -> None:
    if email in _FAKE_USERS:
        raise CognitoError("An account with the given email already exists.", "UsernameExistsException")
    _FAKE_USERS[email] = {"password": password, "role": role, "confirmed": False}


def _fake_confirm(email: str, code: str) -> None:
    record = _FAKE_USERS.get(email)
    if not record:
        raise CognitoError("Invalid verification code.", "CodeMismatchException")
    if record["confirmed"]:
        raise CognitoError("User is already confirmed.", "NotAuthorizedException")
    if code != FAKE_CONFIRM_CODE:
        raise CognitoError("Invalid verification code.", "CodeMismatchException")
    record["confirmed"] = True


def _fake_resend(email: str) -> None:
    record = _FAKE_USERS.get(email)
    if not record:
        raise CognitoError("User not found.", "UserNotFoundException")
    record["confirmed"] = False


def _fake_login(email: str, password: str) -> dict:
    record = _FAKE_USERS.get(email)
    if not record or record["password"] != password:
        raise CognitoError("Incorrect username or password.", "NotAuthorizedException")
    if not record["confirmed"]:
        # Same friendly copy production returns for UserNotConfirmedException.
        raise CognitoError("Please verify your email address before signing in.", "UserNotConfirmedException")
    user = User.objects.filter(email__iexact=email).first()
    pk = user.pk if user else 0
    return {
        "access": f"fake.{pk}.token",
        "refresh": f"fake-refresh.{pk}",
        "expires_in": 3600,
    }


def _fake_forgot(email: str) -> None:
    if email not in _FAKE_USERS:
        # Match Cognito's silence to prevent account enumeration.
        return


def _fake_confirm_forgot(email: str, code: str, new_password: str) -> None:
    record = _FAKE_USERS.get(email)
    if not record:
        raise CognitoError("Invalid verification code.", "CodeMismatchException")
    if code != FAKE_CONFIRM_CODE:
        raise CognitoError("Invalid verification code.", "CodeMismatchException")
    record["password"] = new_password

# ---------------------------------------------------------------------------
# real backend (boto3 against the provisioned User Pool)
# ---------------------------------------------------------------------------

def _client():
    import boto3
    from botocore.config import Config

    return boto3.client(
        "cognito-idp",
        region_name=settings.COGNITO_REGION,
        config=Config(connect_timeout=6, read_timeout=10, retries={"max_attempts": 2}),
    )


def _aws_error(error: Exception) -> CognitoError:
    response = getattr(error, "response", {})
    code = response.get("Error", {}).get("Code", "")
    friendly = {
        "UsernameExistsException": "An account with this email already exists.",
        "InvalidPasswordException": "Password does not meet the requirements.",
        "CodeMismatchException": "That verification code is not correct.",
        "ExpiredCodeException": "This code has expired. Request a new one.",
        "UserNotConfirmedException": "Please verify your email address before signing in.",
        "NotAuthorizedException": "Incorrect email or password.",
        "UserNotFoundException": "No account found for that email address.",
        "TooManyRequestsException": "Too many attempts. Please wait a moment and try again.",
        "LimitExceededException": "Too many attempts. Please try again later.",
        "InvalidParameterException": "Please check the submitted values.",
    }.get(code, "Authentication service error. Please try again.")
    return CognitoError(friendly, code)


def sign_up(*, email: str, password: str, role: str) -> None:
    """Register the user in Cognito with custom:role; triggers the OTP email."""
    if settings.COGNITO_FAKE:
        return _fake_sign_up(email.strip().lower(), password, role)
    try:
        _client().sign_up(
            ClientId=settings.COGNITO_APP_CLIENT_ID,
            Username=email.strip().lower(),
            Password=password,
            UserAttributes=[
                {"Name": "email", "Value": email.strip().lower()},
                {"Name": "custom:role", "Value": role},
            ],
        )
    except Exception as error:  # noqa: BLE001
        raise _aws_error(error) from error


def confirm_sign_up(*, email: str, code: str) -> None:
    """Confirm the emailed OTP; flips the account to verified in Cognito."""
    if settings.COGNITO_FAKE:
        return _fake_confirm(email.strip().lower(), code.strip())
    try:
        _client().confirm_sign_up(
            ClientId=settings.COGNITO_APP_CLIENT_ID,
            Username=email.strip().lower(),
            ConfirmationCode=code.strip(),
        )
    except Exception as error:  # noqa: BLE001
        raise _aws_error(error) from error


def resend_confirmation_code(*, email: str) -> None:
    if settings.COGNITO_FAKE:
        return _fake_resend(email.strip().lower())
    try:
        _client().resend_confirmation_code(
            ClientId=settings.COGNITO_APP_CLIENT_ID,
            Username=email.strip().lower(),
        )
    except Exception as error:  # noqa: BLE001
        raise _aws_error(error) from error


def login(*, identifier: str, password: str) -> dict:
    """PASSWORD grant. Accepts username or email; returns Cognito tokens."""
    email = _resolve_login_email(identifier)
    if settings.COGNITO_FAKE:
        return _fake_login(email, password)
    try:
        result = _client().initiate_auth(
            ClientId=settings.COGNITO_APP_CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": email, "PASSWORD": password},
        )
    except Exception as error:  # noqa: BLE001
        raise _aws_error(error) from error
    return _tokens(result)


def refresh_token(*, refresh_token: str) -> dict:
    """REFRESH_TOKEN grant. Exchanges a Cognito or local refresh token for fresh access tokens."""
    if not refresh_token:
        raise CognitoError("Refresh token is required.", "InvalidParameterException")

    if settings.COGNITO_FAKE or refresh_token.startswith("fake-refresh."):
        parts = refresh_token.split(".")
        if len(parts) == 2 and parts[0] == "fake-refresh":
            try:
                user = User.objects.get(pk=int(parts[1]), is_active=True)
                return {
                    "access": f"fake.{user.pk}.token",
                    "refresh": refresh_token,
                    "expires_in": 3600,
                }
            except (ValueError, User.DoesNotExist):
                raise CognitoError("Session expired or invalid.", "NotAuthorizedException") from None
        raise CognitoError("Invalid refresh token.", "NotAuthorizedException")

    try:
        result = _client().initiate_auth(
            ClientId=settings.COGNITO_APP_CLIENT_ID,
            AuthFlow="REFRESH_TOKEN_AUTH",
            AuthParameters={"REFRESH_TOKEN": refresh_token},
        )
    except Exception as error:  # noqa: BLE001
        raise _aws_error(error) from error

    auth = result.get("AuthenticationResult", {})
    if not auth.get("AccessToken"):
        raise CognitoError("Authentication failed.", "NotAuthorizedException")

    return {
        "access": auth["AccessToken"],
        # Cognito REFRESH_TOKEN_AUTH does not always issue a new refresh token; preserve the current one.
        "refresh": auth.get("RefreshToken") or refresh_token,
        "id_token": auth.get("IdToken", ""),
        "expires_in": auth.get("ExpiresIn", 3600),
    }


def forgot_password(*, email: str) -> None:
    """Emails a reset code. Deliberately silent for unknown addresses."""
    if settings.COGNITO_FAKE:
        return _fake_forgot(email.strip().lower())
    try:
        _client().forgot_password(
            ClientId=settings.COGNITO_APP_CLIENT_ID,
            Username=email.strip().lower(),
        )
    except Exception as error:  # noqa: BLE001
        raise _aws_error(error) from error


def confirm_forgot_password(*, email: str, code: str, new_password: str) -> None:
    if settings.COGNITO_FAKE:
        return _fake_confirm_forgot(email.strip().lower(), code.strip(), new_password)
    try:
        _client().confirm_forgot_password(
            ClientId=settings.COGNITO_APP_CLIENT_ID,
            Username=email.strip().lower(),
            ConfirmationCode=code.strip(),
            Password=new_password,
        )
    except Exception as error:  # noqa: BLE001
        raise _aws_error(error) from error


def delete_user(*, sub: str = "", email: str = "") -> None:
    """Permanently remove an account from the user pool (AdminDeleteUser).

    Called exclusively by the owner panel when an account is deleted, so the
    freed email can sign up again instead of failing with
    "An account with the given email already exists".

    Identity resolution happens server-side only: prefer the immutable Cognito
    ``sub`` recorded at login, falling back to the login email (this pool keys
    users by their verified email address). Never accepts client-supplied IDs.

    Idempotent by design: an identity that is already absent from the pool is
    treated as successfully deleted, so retries and pre-existing drift can
    never block removal of the application data.
    """
    identifier = (sub or "").strip() or (email or "").strip().lower()
    if not identifier:
        raise CognitoError("No Cognito identity available for this account.")

    if settings.COGNITO_FAKE:
        target = (email or identifier).strip().lower()
        _FAKE_USERS.pop(target, None)
        return

    try:
        _client().admin_delete_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=identifier,
        )
    except Exception as error:  # noqa: BLE001
        response = getattr(error, "response", None) or {}
        aws_code = (response.get("Error") or {}).get("Code", "")
        if aws_code in {"UserNotFoundException", "ResourceNotFoundException"}:
            return  # Already gone - idempotent success.
        raise _aws_error(error) from error


