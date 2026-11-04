"""Tests for influencer profile, profile image upload, and related API behaviour.

Key bugs verified here:
  Bug #2 — InfluencerProfileView used to return a relative `profile_image` URL
            (e.g. "profiles/image.jpg") because the serializer was instantiated
            without `context={"request": request}`.  DRF's ImageField only builds
            an absolute URL when the request is present in the serializer context.
            After the fix the own-profile endpoint returns the same absolute URL
            as the business-facing /api/influencers/<id>/ endpoint.
  HTTP 403 /api/influencer/profile/ —
            Verified that business accounts calling this endpoint receive 403 Forbidden
            with a clear permission message, unauthenticated calls receive 401,
            and an influencer account without a profile receives 404.
"""

import io
from PIL import Image as PILImage

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.cognito import FAKE_CONFIRM_CODE, _FAKE_USERS
from accounts.models import UserRole
from django.contrib.auth.models import User
from influencers.models import InfluencerProfile

TEST_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "influencer-profile-tests",
    }
}

INFLUENCER_PAYLOAD = {
    "username": "photo-creator",
    "email": "photo-creator@example.com",
    "password": "safe-password-123",
    "full_name": "Photo Creator",
    "category": "Travel",
    "language": "English",
    "followers": 5000,
    "city": "Mumbai",
    "state": "Maharashtra",
}

OTHER_INFLUENCER_PAYLOAD = {
    "username": "other-creator",
    "email": "other-creator@example.com",
    "password": "safe-password-123",
    "full_name": "Other Creator",
    "category": "Tech",
    "language": "Hindi",
    "followers": 10000,
    "city": "Delhi",
    "state": "Delhi",
}

BUSINESS_PAYLOAD = {
    "username": "photo-brand",
    "email": "photo-brand@example.com",
    "password": "safe-password-123",
    "company_name": "Photo Brand Co",
    "industry": "Tourism",
    "phone": "9876543210",
    "city": "Mumbai",
    "state": "Maharashtra",
}


def _minimal_png_file(filename="test_photo.png", width=8, height=8) -> SimpleUploadedFile:
    """Return a SimpleUploadedFile with a small, valid PNG image and proper filename extension."""
    buf = io.BytesIO()
    img = PILImage.new("RGB", (width, height), color=(120, 80, 200))
    img.save(buf, format="PNG")
    return SimpleUploadedFile(filename, buf.getvalue(), content_type="image/png")


@override_settings(CACHES=TEST_CACHES)
class InfluencerProfileImageTests(APITestCase):
    """
    Verify that profile_image is returned as a full absolute URL on both the
    own-profile endpoint and the business-facing influencer detail endpoint,
    and enforce authentication and role boundaries on /api/influencer/profile/.
    """

    def setUp(self):
        _FAKE_USERS.clear()
        self.influencer = self._register_and_login_influencer()
        self.business_tokens = self._register_and_get_business_tokens()

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _verify(self, email):
        r = self.client.post(
            "/api/verify-email/",
            {"email": email, "code": FAKE_CONFIRM_CODE},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def _register_and_login_influencer(self):
        r = self.client.post("/api/influencer/register/", INFLUENCER_PAYLOAD, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self._verify(INFLUENCER_PAYLOAD["email"])
        login = self.client.post(
            "/api/login/",
            {"username": INFLUENCER_PAYLOAD["username"], "password": INFLUENCER_PAYLOAD["password"]},
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        return InfluencerProfile.objects.get(user__username=INFLUENCER_PAYLOAD["username"])

    def _register_and_get_business_tokens(self):
        r = self.client.post("/api/business/register/", BUSINESS_PAYLOAD, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self._verify(BUSINESS_PAYLOAD["email"])
        login = self.client.post(
            "/api/login/",
            {"username": BUSINESS_PAYLOAD["username"], "password": BUSINESS_PAYLOAD["password"]},
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        return login.data["access"]

    def _set_influencer_auth(self):
        login = self.client.post(
            "/api/login/",
            {"username": INFLUENCER_PAYLOAD["username"], "password": INFLUENCER_PAYLOAD["password"]},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def _set_business_auth(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.business_tokens}")

    # -----------------------------------------------------------------------
    # Tests
    # -----------------------------------------------------------------------

    def test_own_profile_image_is_absent_before_upload(self):
        """profile_image must be None/null before any upload."""
        self._set_influencer_auth()
        r = self.client.get("/api/influencer/profile/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIsNone(r.data.get("profile_image"))

    def test_influencer_can_upload_profile_image_via_patch(self):
        """PATCH /api/influencer/profile/ with a valid PNG must succeed."""
        self._set_influencer_auth()
        uploaded_file = _minimal_png_file()
        r = self.client.patch(
            "/api/influencer/profile/",
            {"profile_image": uploaded_file},
            format="multipart",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.assertIsNotNone(r.data.get("profile_image"))

    def test_own_profile_image_is_absolute_url_after_upload(self):
        """
        Bug #2 regression test.

        After upload, GET /api/influencer/profile/ must return an absolute URL
        (starts with http:// or https://) rather than a bare relative path like
        "profiles/image.png".  The fix passes `context={"request": request}` to
        the serializer so DRF's ImageField can build the full URL.
        """
        self._set_influencer_auth()
        # Upload
        self.client.patch(
            "/api/influencer/profile/",
            {"profile_image": _minimal_png_file()},
            format="multipart",
        )
        # Fetch own profile
        r = self.client.get("/api/influencer/profile/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        image_url = r.data.get("profile_image")
        self.assertIsNotNone(image_url, "profile_image must not be null after upload")
        self.assertTrue(
            image_url.startswith("http://") or image_url.startswith("https://"),
            f"Expected an absolute URL; got: {image_url!r}",
        )

    def test_business_facing_profile_image_is_absolute_url(self):
        """
        The business-facing /api/influencers/<id>/ endpoint (RetrieveAPIView)
        has always injected the request context automatically.  Verify the URL
        is absolute here too so we catch any regression on that endpoint.
        """
        # Upload as influencer
        self._set_influencer_auth()
        self.client.patch(
            "/api/influencer/profile/",
            {"profile_image": _minimal_png_file()},
            format="multipart",
        )

        # Fetch via business endpoint
        self._set_business_auth()
        r = self.client.get(f"/api/influencers/{self.influencer.id}/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        image_url = r.data.get("profile_image")
        self.assertIsNotNone(image_url)
        self.assertTrue(
            image_url.startswith("http://") or image_url.startswith("https://"),
            f"Expected absolute URL from business endpoint; got: {image_url!r}",
        )

    def test_own_profile_and_business_profile_return_same_image_url(self):
        """
        After upload the own-profile endpoint and the business-facing detail
        endpoint must return the same image URL (modulo host differences that
        arise from test client vs. real server, so we compare the path portion).
        """
        self._set_influencer_auth()
        self.client.patch(
            "/api/influencer/profile/",
            {"profile_image": _minimal_png_file()},
            format="multipart",
        )

        own_r = self.client.get("/api/influencer/profile/")
        own_url = own_r.data.get("profile_image", "")

        self._set_business_auth()
        biz_r = self.client.get(f"/api/influencers/{self.influencer.id}/")
        biz_url = biz_r.data.get("profile_image", "")

        # Both should contain the same path suffix (strip scheme+host for comparison)
        from urllib.parse import urlparse
        own_path = urlparse(own_url).path
        biz_path = urlparse(biz_url).path
        self.assertEqual(own_path, biz_path, "Own-profile and business-profile image paths must match")

    def test_profile_image_persists_after_reload(self):
        """Image URL is stored in the DB; a fresh GET after upload returns it."""
        self._set_influencer_auth()
        self.client.patch(
            "/api/influencer/profile/",
            {"profile_image": _minimal_png_file()},
            format="multipart",
        )
        # Second GET simulates a page reload
        r = self.client.get("/api/influencer/profile/")
        self.assertIsNotNone(r.data.get("profile_image"))

    def test_unauthorized_upload_returns_401_or_403(self):
        """An unauthenticated request to upload a profile image must be rejected."""
        self.client.credentials()  # clear auth
        r = self.client.patch(
            "/api/influencer/profile/",
            {"profile_image": _minimal_png_file()},
            format="multipart",
        )
        self.assertIn(r.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_unauthenticated_get_profile_returns_401(self):
        """An unauthenticated GET to /api/influencer/profile/ returns 401."""
        self.client.credentials()  # clear auth
        r = self.client.get("/api/influencer/profile/")
        self.assertIn(r.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_business_user_calling_influencer_profile_returns_403(self):
        """
        Confirmed HTTP 403 root cause test:
        When a business user calls /api/influencer/profile/, IsInfluencerUser
        rejects the request with 403 Forbidden and the exact message:
        'Only influencer accounts can perform this action.'
        """
        self._set_business_auth()
        r = self.client.get("/api/influencer/profile/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(r.data.get("detail"), "Only influencer accounts can perform this action.")

    def test_business_user_cannot_upload_influencer_profile_image(self):
        """A business account must not be able to mutate an influencer's profile image."""
        self._set_business_auth()
        r = self.client.patch(
            "/api/influencer/profile/",
            {"profile_image": _minimal_png_file()},
            format="multipart",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_influencer_without_profile_returns_404_not_found(self):
        """
        An authenticated user with influencer role but no profile in DB
        receives a 404 response rather than an unhandled 500 error.
        """
        # Register second influencer
        r = self.client.post("/api/influencer/register/", OTHER_INFLUENCER_PAYLOAD, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self._verify(OTHER_INFLUENCER_PAYLOAD["email"])

        # Delete the profile to simulate missing profile state
        InfluencerProfile.objects.filter(user__username=OTHER_INFLUENCER_PAYLOAD["username"]).delete()

        # Log in
        login = self.client.post(
            "/api/login/",
            {"username": OTHER_INFLUENCER_PAYLOAD["username"], "password": OTHER_INFLUENCER_PAYLOAD["password"]},
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

        # Fetch profile
        r = self.client.get("/api/influencer/profile/")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(r.data.get("error"), "Profile not found")

    def test_user_cannot_modify_or_view_other_influencer_profile(self):
        """
        Users cannot pass an ID to view or mutate another influencer's profile;
        the endpoint operates strictly on request.user.
        """
        # Register second influencer
        r = self.client.post("/api/influencer/register/", OTHER_INFLUENCER_PAYLOAD, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self._verify(OTHER_INFLUENCER_PAYLOAD["email"])
        other_prof = InfluencerProfile.objects.get(user__username=OTHER_INFLUENCER_PAYLOAD["username"])

        # Authenticated as first influencer
        self._set_influencer_auth()
        # GET returns first influencer's data only
        r = self.client.get("/api/influencer/profile/")
        self.assertEqual(r.data["id"], self.influencer.id)
        self.assertNotEqual(r.data["id"], other_prof.id)

        # PATCH updates first influencer's bio, cannot affect second
        patch_r = self.client.patch("/api/influencer/profile/", {"bio": "Updated bio for creator 1"}, format="json")
        self.assertEqual(patch_r.status_code, status.HTTP_200_OK)
        self.influencer.refresh_from_db()
        other_prof.refresh_from_db()
        self.assertEqual(self.influencer.bio, "Updated bio for creator 1")
        self.assertNotEqual(other_prof.bio, "Updated bio for creator 1")

    def test_missing_profile_image_returns_null_not_error(self):
        """A profile without a photo must return null for profile_image, not raise an exception."""
        self._set_influencer_auth()
        r = self.client.get("/api/influencer/profile/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("profile_image", r.data)
        # The value should be falsy (None or "")
        self.assertFalse(r.data["profile_image"])

    def test_upload_updates_completion_percentage(self):
        """Uploading a profile image must increase the completion_percentage."""
        self._set_influencer_auth()
        before = self.client.get("/api/influencer/profile/").data["completion_percentage"]
        self.client.patch(
            "/api/influencer/profile/",
            {"profile_image": _minimal_png_file()},
            format="multipart",
        )
        after = self.client.get("/api/influencer/profile/").data["completion_percentage"]
        self.assertGreater(after, before, "completion_percentage must increase after image upload")


@override_settings(CACHES=TEST_CACHES)
class InfluencerDirectoryAccessMatrixTests(APITestCase):
    """
    Test matrix for /api/influencers/ and /api/influencers/<id>/ across all 4 access conditions:
    1. Authenticated business account -> HTTP 200 OK
    2. Authenticated influencer account -> HTTP 403 Forbidden
    3. Unauthenticated caller -> HTTP 401 Unauthorized
    4. Authenticated unauthorized account (no business profile) -> HTTP 403 Forbidden
    Additional condition:
    5. Authenticated owner / staff account -> HTTP 200 OK
    """

    def setUp(self):
        _FAKE_USERS.clear()
        # Create influencer
        self.influencer_user = User.objects.create_user(
            username="matrix-influencer",
            email="matrix-influencer@example.com",
            password="safe-password-123",
            is_active=True,
        )
        UserRole.objects.create(user=self.influencer_user, role="influencer")
        self.influencer_profile = InfluencerProfile.objects.create(
            user=self.influencer_user,
            full_name="Matrix Influencer",
            category="Tech",
            language="English",
            followers=15000,
            city="Bengaluru",
            state="Karnataka",
            email_verified=True,
        )

        # Create business
        from businesses.models import BusinessProfile
        self.business_user = User.objects.create_user(
            username="matrix-business",
            email="matrix-business@example.com",
            password="safe-password-123",
            is_active=True,
        )
        UserRole.objects.create(user=self.business_user, role="business")
        self.business_profile = BusinessProfile.objects.create(
            user=self.business_user,
            company_name="Matrix Tech Brands",
            industry="Technology",
            phone="9876543210",
            city="Bengaluru",
            state="Karnataka",
        )

        # Create user without role/profile
        self.plain_user = User.objects.create_user(
            username="matrix-plain",
            email="matrix-plain@example.com",
            password="safe-password-123",
            is_active=True,
        )

        # Create owner user
        self.owner_user = User.objects.create_user(
            username="matrix-owner",
            email="matrix-owner@example.com",
            password="safe-password-123",
            is_active=True,
        )
        UserRole.objects.create(user=self.owner_user, role="owner")

    def _login(self, username):
        res = self.client.post("/api/login/", {"username": username, "password": "safe-password-123"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        return res.data

    def test_condition_1_authenticated_business_can_browse_directory(self):
        """Condition 1: Authenticated business retrieves directory with 200 OK."""
        self._login("matrix-business")
        res = self.client.get("/api/influencers/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("results", res.data)
        self.assertGreaterEqual(res.data["count"], 1)
        found = any(c["id"] == self.influencer_profile.id for c in res.data["results"])
        self.assertTrue(found, "Created influencer should appear in business directory")

        # Can also fetch single creator detail
        detail_res = self.client.get(f"/api/influencers/{self.influencer_profile.id}/")
        self.assertEqual(detail_res.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_res.data["full_name"], "Matrix Influencer")

    def test_condition_2_authenticated_influencer_receives_403(self):
        """Condition 2: Authenticated influencer is rejected with 403 Forbidden."""
        self._login("matrix-influencer")
        res = self.client.get("/api/influencers/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.data.get("detail"), "Only business accounts can perform this action.")

        # Influencer also cannot fetch single creator detail via business endpoint
        detail_res = self.client.get(f"/api/influencers/{self.influencer_profile.id}/")
        self.assertEqual(detail_res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(detail_res.data.get("detail"), "Only business accounts can perform this action.")

    def test_condition_3_unauthenticated_request_receives_401(self):
        """Condition 3: Unauthenticated caller receives 401 Unauthorized."""
        self.client.credentials()  # clear credentials
        res = self.client.get("/api/influencers/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        detail_res = self.client.get(f"/api/influencers/{self.influencer_profile.id}/")
        self.assertEqual(detail_res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_condition_4_unauthorized_user_without_business_role_receives_403(self):
        """Condition 4: Authenticated user without business profile/role receives 403 Forbidden."""
        self._login("matrix-plain")
        res = self.client.get("/api/influencers/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.data.get("detail"), "Only business accounts can perform this action.")

    def test_condition_5_owner_account_can_browse_directory(self):
        """Condition 5: Authenticated platform owner can browse directory with 200 OK."""
        self._login("matrix-owner")
        res = self.client.get("/api/influencers/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("results", res.data)

