"""Tests for the Cognito-backed signup / OTP verification / login flows.

The suite runs against the in-process fake Cognito backend (settings forces
COGNITO_FAKE during tests), where signups are confirmed with the fixed code
FAKE_CONFIRM_CODE. No test ever talks to AWS.
"""

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.cognito import FAKE_CONFIRM_CODE, _FAKE_USERS

TEST_CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

User = get_user_model()

BUSINESS_PAYLOAD = {
    "username": "brand-cognito",
    "email": "brand-cognito@example.com",
    "password": "safe-password-123",
    "company_name": "Cog Co",
    "industry": "technology",
    "phone": "9876543210",
    "city": "Bengaluru",
    "state": "Karnataka",
}

INFLUENCER_PAYLOAD = {
    "username": "creator-cognito",
    "email": "creator-cognito@example.com",
    "password": "safe-password-123",
    "full_name": "Creator Cog",
    "category": "fitness",
    "language": "English",
    "followers": 1000,
    "city": "Bengaluru",
    "state": "Karnataka",
}


def _clear_fake_pool():
    _FAKE_USERS.clear()


@override_settings(CACHES=TEST_CACHES)
class CognitoSignupVerificationTests(APITestCase):
    def setUp(self):
        _clear_fake_pool()

    def test_business_signup_creates_inactive_local_and_cognito_users(self):
        response = self.client.post("/api/business/register/", BUSINESS_PAYLOAD, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["verification_required"])

        user = User.objects.get(email=BUSINESS_PAYLOAD["email"])
        self.assertFalse(user.is_active)
        # The fake pool received the signup but it is not confirmed yet.
        record = _FAKE_USERS[BUSINESS_PAYLOAD["email"]]
        self.assertEqual(record["role"], "business")
        self.assertFalse(record["confirmed"])

    def test_influencer_signup_creates_inactive_account(self):
        response = self.client.post("/api/influencer/register/", INFLUENCER_PAYLOAD, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        record = _FAKE_USERS[INFLUENCER_PAYLOAD["email"]]
        self.assertEqual(record["role"], "influencer")
        self.assertFalse(User.objects.get(email=INFLUENCER_PAYLOAD["email"]).is_active)

    def test_verify_then_login_returns_tokens_and_role(self):
        payload = {**INFLUENCER_PAYLOAD, "username": "creator-flow", "email": "creator-flow@example.com"}
        self.client.post("/api/influencer/register/", payload, format="json")

        verified = self.client.post(
            "/api/verify-email/", {"email": payload["email"], "code": FAKE_CONFIRM_CODE}, format="json"
        )
        self.assertEqual(verified.status_code, status.HTTP_200_OK)
        self.assertTrue(User.objects.get(email=payload["email"]).is_active)

        login = self.client.post(
            "/api/login/", {"username": payload["username"], "password": payload["password"]}, format="json"
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.assertIn("access", login.data)
        self.assertEqual(login.data["role"], "influencer")

        # The token from login authenticates the protected profile endpoint.
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        me = self.client.get("/api/me/")
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertEqual(me.data["email"], payload["email"])

    def test_wrong_code_rejected_then_correct_code_accepted(self):
        self.client.post("/api/business/register/", BUSINESS_PAYLOAD, format="json")
        wrong = self.client.post(
            "/api/verify-email/", {"email": BUSINESS_PAYLOAD["email"], "code": "000000"}, format="json"
        )
        self.assertEqual(wrong.status_code, status.HTTP_400_BAD_REQUEST)
        right = self.client.post(
            "/api/verify-email/", {"email": BUSINESS_PAYLOAD["email"], "code": FAKE_CONFIRM_CODE}, format="json"
        )
        self.assertEqual(right.status_code, status.HTTP_200_OK)

    def test_duplicate_email_signup_rejected(self):
        first = self.client.post("/api/business/register/", BUSINESS_PAYLOAD, format="json")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        duplicate = {**BUSINESS_PAYLOAD, "username": "another-brand"}
        second = self.client.post("/api/influencer/register/", duplicate, format="json")
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resend_reports_success_for_unverified_account(self):
        payload = {**BUSINESS_PAYLOAD, "username": "brand-resend", "email": "brand-resend@example.com"}
        self.client.post("/api/business/register/", payload, format="json")
        response = self.client.post("/api/resend-verification/", {"email": payload["email"]}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIs(response.data["emailed"], True)
        self.assertEqual(response.data["message"], "Verification code sent to your email.")


@override_settings(CACHES=TEST_CACHES)
class AuthFailureAndResetTests(APITestCase):
    def setUp(self):
        _clear_fake_pool()

    def _signup_and_verify(self, username: str) -> dict:
        payload = {**INFLUENCER_PAYLOAD, "username": username, "email": f"{username}@example.com"}
        self.client.post("/api/influencer/register/", payload, format="json")
        self.client.post("/api/verify-email/", {"email": payload["email"], "code": FAKE_CONFIRM_CODE}, format="json")
        return payload

    def test_login_before_verification_is_rejected_with_clear_message(self):
        self.client.post("/api/influencer/register/", INFLUENCER_PAYLOAD, format="json")
        login = self.client.post(
            "/api/login/",
            {"username": INFLUENCER_PAYLOAD["username"], "password": INFLUENCER_PAYLOAD["password"]},
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("erify", login.data["detail"])

    def test_login_with_wrong_password_rejected(self):
        payload = self._signup_and_verify("wrongpw")
        login = self.client.post(
            "/api/login/", {"username": payload["username"], "password": "definitely-wrong"}, format="json"
        )
        self.assertEqual(login.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_password_reset_flow_changes_the_password(self):
        payload = self._signup_and_verify("resetflow")

        request = self.client.post("/api/forgot-password/", {"email": payload["email"]}, format="json")
        self.assertEqual(request.status_code, status.HTTP_200_OK)

        new_password = "brand-new-password-9"
        confirm = self.client.post(
            "/api/confirm-forgot-password/",
            {"email": payload["email"], "code": FAKE_CONFIRM_CODE, "new_password": new_password},
            format="json",
        )
        self.assertEqual(confirm.status_code, status.HTTP_200_OK)

        old_login = self.client.post(
            "/api/login/", {"username": payload["username"], "password": payload["password"]}, format="json"
        )
        self.assertEqual(old_login.status_code, status.HTTP_401_UNAUTHORIZED)
        new_login = self.client.post(
            "/api/login/", {"username": payload["username"], "password": new_password}, format="json"
        )
        self.assertEqual(new_login.status_code, status.HTTP_200_OK)

    def test_forgot_password_for_unknown_email_stays_silent_but_ok(self):
        response = self.client.post("/api/forgot-password/", {"email": "ghost@example.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_token_refresh_successful_with_valid_refresh_token(self):
        payload = self._signup_and_verify("refreshtest")
        login = self.client.post(
            "/api/login/", {"username": payload["username"], "password": payload["password"]}, format="json"
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        refresh_token = login.data.get("refresh")
        self.assertTrue(refresh_token)

        res = self.client.post("/api/token/refresh/", {"refresh": refresh_token}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

    def test_token_refresh_fails_with_invalid_refresh_token(self):
        res = self.client.post("/api/token/refresh/", {"refresh": "fake-refresh.999999"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)



from accounts.models import EmailVerificationCode
from accounts.services import issue_verification_code, confirm_email_with_code
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
import io
from PIL import Image

def _make_test_image():
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color="purple").save(buf, format="PNG")
    return buf.getvalue()


@override_settings(CACHES=TEST_CACHES)
class EmailVerificationAndUploadTests(APITestCase):
    def setUp(self):
        _clear_fake_pool()

    def test_registration_creates_email_verification_code_record(self):
        payload = {**BUSINESS_PAYLOAD, "username": "otp-biz", "email": "otp-biz@example.com"}
        res = self.client.post("/api/business/register/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data["verification_required"])

        user = User.objects.get(email=payload["email"])
        code_record = EmailVerificationCode.objects.filter(user=user, consumed_at__isnull=True).first()
        self.assertIsNotNone(code_record)
        self.assertEqual(len(code_record.code), 6)

    def test_confirm_with_postgres_generated_code(self):
        payload = {**INFLUENCER_PAYLOAD, "username": "otp-inf", "email": "otp-inf@example.com"}
        self.client.post("/api/influencer/register/", payload, format="json")
        user = User.objects.get(email=payload["email"])
        code_record = EmailVerificationCode.objects.filter(user=user, consumed_at__isnull=True).first()

        verify_res = self.client.post(
            "/api/verify-email/", {"email": payload["email"], "code": code_record.code}, format="json"
        )
        self.assertEqual(verify_res.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        code_record.refresh_from_db()
        self.assertTrue(code_record.is_consumed)

    def test_expired_code_rejected(self):
        payload = {**BUSINESS_PAYLOAD, "username": "expired-biz", "email": "expired-biz@example.com"}
        self.client.post("/api/business/register/", payload, format="json")
        user = User.objects.get(email=payload["email"])
        code_record = EmailVerificationCode.objects.filter(user=user).first()
        code_record.expires_at = timezone.now() - timezone.timedelta(minutes=10)
        code_record.save()

        res = self.client.post("/api/verify-email/", {"email": payload["email"], "code": code_record.code}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("expired", str(res.data).lower())

    def test_otp_attempt_limit_and_lockout(self):
        payload = {**BUSINESS_PAYLOAD, "username": "lockout-biz", "email": "lockout-biz@example.com"}
        self.client.post("/api/business/register/", payload, format="json")
        user = User.objects.get(email=payload["email"])
        code_record = EmailVerificationCode.objects.filter(user=user, consumed_at__isnull=True).first()
        real_code = code_record.code

        # Attempts 1-4 with wrong code
        for i in range(1, 5):
            res = self.client.post("/api/verify-email/", {"email": payload["email"], "code": "000000"}, format="json")
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            remaining = 5 - i
            self.assertIn(f"{remaining} attempt", str(res.data))

        # 5th attempt locks out
        res5 = self.client.post("/api/verify-email/", {"email": payload["email"], "code": "000000"}, format="json")
        self.assertEqual(res5.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("too many failed attempts", str(res5.data).lower())

        # Correct code now fails because the OTP was deactivated
        res_real = self.client.post("/api/verify-email/", {"email": payload["email"], "code": real_code}, format="json")
        self.assertEqual(res_real.status_code, status.HTTP_400_BAD_REQUEST)

    def test_consumed_code_cannot_be_reused(self):
        payload = {**BUSINESS_PAYLOAD, "username": "reuse-biz", "email": "reuse-biz@example.com"}
        self.client.post("/api/business/register/", payload, format="json")
        user = User.objects.get(email=payload["email"])
        code_record = EmailVerificationCode.objects.filter(user=user).first()

        # First verification
        res1 = self.client.post("/api/verify-email/", {"email": payload["email"], "code": code_record.code}, format="json")
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        # Second verification attempt with same code
        res2 = self.client.post("/api/verify-email/", {"email": payload["email"], "code": code_record.code}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_registration_handling(self):
        payload = {**BUSINESS_PAYLOAD, "username": "dup-biz", "email": "dup-biz@example.com"}
        self.client.post("/api/business/register/", payload, format="json")

        # Duplicate submission when unverified
        res2 = self.client.post("/api/business/register/", payload, format="json")
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("unverified", str(res2.data).lower())

        # Now verify user
        user = User.objects.get(email=payload["email"])
        user.is_active = True
        user.save()

        # Duplicate submission when verified
        res3 = self.client.post("/api/business/register/", payload, format="json")
        self.assertEqual(res3.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already exists", str(res3.data).lower())

    def test_resend_cooldown_enforced_when_configured(self):
        payload = {**BUSINESS_PAYLOAD, "username": "cool-biz", "email": "cool-biz@example.com"}
        self.client.post("/api/business/register/", payload, format="json")

        with override_settings(EMAIL_RESEND_COOLDOWN_SECONDS=60):
            resend = self.client.post("/api/resend-verification/", {"email": payload["email"]}, format="json")
            self.assertEqual(resend.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("wait", str(resend.data).lower())

    def test_logo_upload_requires_authentication_and_business_role(self):
        # Unauthenticated request fails
        img_bytes = _make_test_image()
        logo_file = SimpleUploadedFile("logo.png", img_bytes, content_type="image/png")
        unauth = self.client.put("/api/business/profile/", {"logo": logo_file}, format="multipart")
        self.assertEqual(unauth.status_code, status.HTTP_401_UNAUTHORIZED)

        # Influencer cannot upload to business profile
        inf_payload = {**INFLUENCER_PAYLOAD, "username": "role-test-inf", "email": "role-test-inf@example.com"}
        self.client.post("/api/influencer/register/", inf_payload, format="json")
        self.client.post("/api/verify-email/", {"email": inf_payload["email"], "code": FAKE_CONFIRM_CODE}, format="json")
        login = self.client.post("/api/login/", {"username": inf_payload["username"], "password": inf_payload["password"]}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

        wrong_role = self.client.put("/api/business/profile/", {"logo": logo_file}, format="multipart")
        self.assertEqual(wrong_role.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_invalid_file_type_rejected(self):
        biz_payload = {**BUSINESS_PAYLOAD, "username": "upload-biz", "email": "upload-biz@example.com"}
        self.client.post("/api/business/register/", biz_payload, format="json")
        self.client.post("/api/verify-email/", {"email": biz_payload["email"], "code": FAKE_CONFIRM_CODE}, format="json")
        login = self.client.post("/api/login/", {"username": biz_payload["username"], "password": biz_payload["password"]}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

        fake_exe = SimpleUploadedFile("dangerous.exe", b"binary content", content_type="application/octet-stream")
        res = self.client.put("/api/business/profile/", {"logo": fake_exe}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
