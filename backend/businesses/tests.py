"""Tests for business profile, logo upload, and absolute URL generation."""

import io
from PIL import Image as PILImage

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.cognito import FAKE_CONFIRM_CODE, _FAKE_USERS
from businesses.models import BusinessProfile

TEST_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "business-profile-tests",
    }
}

BUSINESS_PAYLOAD = {
    "username": "brand-logo-test",
    "email": "brand-logo-test@example.com",
    "password": "safe-password-123",
    "company_name": "Brand Logo Co",
    "industry": "Retail",
    "phone": "9876543210",
    "city": "Mumbai",
    "state": "Maharashtra",
}

INFLUENCER_PAYLOAD = {
    "username": "influencer-tester",
    "email": "influencer-tester@example.com",
    "password": "safe-password-123",
    "full_name": "Influencer Tester",
    "category": "Fashion",
    "language": "English",
    "followers": 15000,
    "city": "Delhi",
    "state": "Delhi",
}


def _minimal_png_file(filename="logo.png", width=8, height=8) -> SimpleUploadedFile:
    buf = io.BytesIO()
    img = PILImage.new("RGB", (width, height), color=(60, 120, 240))
    img.save(buf, format="PNG")
    return SimpleUploadedFile(filename, buf.getvalue(), content_type="image/png")


@override_settings(CACHES=TEST_CACHES)
class BusinessProfileLogoTests(APITestCase):
    def setUp(self):
        _FAKE_USERS.clear()
        self.business = self._register_and_login_business()

    def _verify(self, email):
        r = self.client.post("/api/verify-email/", {"email": email, "code": FAKE_CONFIRM_CODE}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def _register_and_login_business(self):
        r = self.client.post("/api/business/register/", BUSINESS_PAYLOAD, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self._verify(BUSINESS_PAYLOAD["email"])
        login = self.client.post(
            "/api/login/",
            {"username": BUSINESS_PAYLOAD["username"], "password": BUSINESS_PAYLOAD["password"]},
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        return BusinessProfile.objects.get(user__username=BUSINESS_PAYLOAD["username"])

    def test_logo_is_none_before_upload(self):
        r = self.client.get("/api/business/profile/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIsNone(r.data.get("logo"))

    def test_business_can_upload_logo(self):
        uploaded_logo = _minimal_png_file()
        r = self.client.put(
            "/api/business/profile/",
            {"logo": uploaded_logo},
            format="multipart",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.assertIsNotNone(r.data.get("logo"))

    def test_business_logo_is_absolute_url_after_upload(self):
        # Upload logo
        self.client.put(
            "/api/business/profile/",
            {"logo": _minimal_png_file()},
            format="multipart",
        )
        # GET profile
        r = self.client.get("/api/business/profile/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        logo_url = r.data.get("logo")
        self.assertIsNotNone(logo_url, "logo must not be null after upload")
        self.assertTrue(
            logo_url.startswith("http://") or logo_url.startswith("https://"),
            f"Expected an absolute URL for business logo; got: {logo_url!r}",
        )

    def test_business_logo_persists_on_fresh_get(self):
        self.client.put(
            "/api/business/profile/",
            {"logo": _minimal_png_file()},
            format="multipart",
        )
        r = self.client.get("/api/business/profile/")
        self.assertIsNotNone(r.data.get("logo"))

    def test_influencer_cannot_access_or_upload_business_profile(self):
        # Register and log in influencer
        r = self.client.post("/api/influencer/register/", INFLUENCER_PAYLOAD, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self._verify(INFLUENCER_PAYLOAD["email"])
        login = self.client.post(
            "/api/login/",
            {"username": INFLUENCER_PAYLOAD["username"], "password": INFLUENCER_PAYLOAD["password"]},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

        # Attempt to access business profile
        r = self.client.get("/api/business/profile/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(r.data.get("detail"), "Only business accounts can perform this action.")
