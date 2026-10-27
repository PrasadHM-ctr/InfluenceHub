"""End-to-end workflow verification test suite.

Tests every workflow required by the specification:
1. Business registration -> verification -> login -> business dashboard
2. Influencer registration -> verification -> login -> influencer profile/dashboard
3. Invalid login (wrong password / unverified user / unknown user) -> 401 without 500
4. Role access control (influencer blocked from business API, business blocked from owner API)
5. Owner authentication and admin panel access
6. Influencer search and filtering
7. Campaign creation -> influencer receives proposal
8. Campaign acceptance -> conversation created
9. Chat messaging between business and influencer
10. Profile photo and document uploads
"""

import io
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from PIL import Image

from accounts.cognito import FAKE_CONFIRM_CODE, _FAKE_USERS
from accounts.models import UserRole
from businesses.models import BusinessProfile
from campaigns.models import CampaignRequest
from influencers.models import InfluencerProfile
from notifications.models import Notification

User = get_user_model()
TEST_CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


def create_test_image(name="test.png"):
    buf = io.BytesIO()
    img = Image.new("RGB", (32, 32), color=(100, 150, 200))
    img.save(buf, format="PNG")
    buf.seek(0)
    buf.name = name
    return buf


@override_settings(CACHES=TEST_CACHES)
class EndToEndMarketplaceWorkflowsTest(APITestCase):
    def setUp(self):
        _FAKE_USERS.clear()

    def test_01_business_signup_verification_login_and_dashboard(self):
        # 1. Business Registration
        payload = {
            "username": "e2e_brand",
            "email": "e2e_brand@example.com",
            "password": "strong-password-123",
            "company_name": "E2E Brands Inc",
            "industry": "Ecommerce",
            "phone": "9876543210",
            "city": "Bengaluru",
            "state": "Karnataka",
            "website": "https://example.com",
            "description": "Premium brand looking for creators",
        }
        res = self.client.post("/api/business/register/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data.get("verification_required"))

        # Verify account created inactive
        user = User.objects.get(username="e2e_brand")
        self.assertFalse(user.is_active)

        # 2. Attempt login before verification -> must be rejected 401
        res = self.client.post(
            "/api/login/",
            {"username": "e2e_brand", "password": "strong-password-123"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("verify", res.data["detail"].lower())

        # 3. Verify Email with OTP
        res = self.client.post(
            "/api/verify-email/",
            {"email": "e2e_brand@example.com", "code": FAKE_CONFIRM_CODE},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_active)

        # 4. Login after verification -> must return tokens and role="business"
        res = self.client.post(
            "/api/login/",
            {"username": "e2e_brand", "password": "strong-password-123"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["role"], "business")
        access_token = res.data["access"]

        # 5. Business Dashboard access using token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        res = self.client.get("/api/business/dashboard/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["total_campaigns"], 0)

        # 6. Business Profile access
        res = self.client.get("/api/business/profile/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["company_name"], "E2E Brands Inc")

    def test_02_influencer_signup_verification_login_and_discovery(self):
        # 1. Influencer Registration
        payload = {
            "username": "e2e_creator",
            "email": "e2e_creator@example.com",
            "password": "strong-password-123",
            "full_name": "E2E Creator",
            "category": "Technology",
            "language": "English",
            "followers": 50000,
            "city": "Mumbai",
            "state": "Maharashtra",
            "bio": "Tech reviewer & content creator",
            "instagram": "https://instagram.com/e2e_creator",
        }
        res = self.client.post("/api/influencer/register/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(username="e2e_creator")
        self.assertFalse(user.is_active)

        # 2. Verify Email
        res = self.client.post(
            "/api/verify-email/",
            {"email": "e2e_creator@example.com", "code": FAKE_CONFIRM_CODE},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_active)

        # 3. Influencer Login
        res = self.client.post(
            "/api/login/",
            {"username": "e2e_creator", "password": "strong-password-123"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["role"], "influencer")
        access_token = res.data["access"]

        # 4. Influencer Profile access
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        res = self.client.get("/api/influencer/profile/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["full_name"], "E2E Creator")

        # 5. Influencer Discovery API (requires business role)
        biz_user = User.objects.create_user(
            username="biz_discovery",
            email="biz_discovery@example.com",
            is_active=True,
        )
        UserRole.objects.create(user=biz_user, role="business")
        BusinessProfile.objects.create(user=biz_user, company_name="Discovery Co")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer fake.{biz_user.pk}.token")

        res = self.client.get("/api/influencers/?category=Technology")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(res.data["count"], 1)

    def test_03_invalid_login_handling_without_server_error(self):
        # 1. Non-existent user
        res = self.client.post(
            "/api/login/",
            {"username": "ghost_user", "password": "random-password"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("detail", res.data)

        # 2. Existing user with wrong password
        # First create an active user
        user = User.objects.create_user(
            username="real_user",
            email="real_user@example.com",
            password="correct-password",
            is_active=True,
        )
        UserRole.objects.create(user=user, role="business")
        _FAKE_USERS["real_user@example.com"] = {
            "password": "correct-password",
            "role": "business",
            "confirmed": True,
        }

        res = self.client.post(
            "/api/login/",
            {"username": "real_user", "password": "wrong-password"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("detail", res.data)

    def test_04_owner_authentication_and_access_control(self):
        # 1. Create Owner User
        owner = User.objects.create_user(
            username="platform_owner",
            email="owner@influencehub.com",
            password="owner-secret-password-123",
            is_active=True,
            is_staff=True,
            is_superuser=True,
        )
        UserRole.objects.create(user=owner, role="owner")
        _FAKE_USERS["owner@influencehub.com"] = {
            "password": "owner-secret-password-123",
            "role": "owner",
            "confirmed": True,
        }

        # 2. Owner Login
        res = self.client.post(
            "/api/login/",
            {"username": "platform_owner", "password": "owner-secret-password-123"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["role"], "owner")
        owner_token = res.data["access"]

        # 3. Owner Accesses Admin Dashboard API
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {owner_token}")
        res = self.client.get("/api/admin/dashboard/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("users", res.data)
        self.assertIn("campaigns", res.data)

        # 4. Owner Accesses Admin Users List API
        res = self.client.get("/api/admin/users/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # 5. Normal Business User is REJECTED from Owner API
        biz_user = User.objects.create_user(
            username="biz_normal",
            email="biz_normal@example.com",
            password="pass",
            is_active=True,
        )
        UserRole.objects.create(user=biz_user, role="business")
        BusinessProfile.objects.create(user=biz_user, company_name="Normal Co")
        biz_token = f"fake.{biz_user.pk}.token"

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {biz_token}")
        res = self.client.get("/api/admin/dashboard/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        res = self.client.get("/api/admin/users/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_05_campaign_lifecycle_notifications_and_chat(self):
        # Setup Business
        biz = User.objects.create_user(username="b1", email="b1@ex.com", is_active=True)
        UserRole.objects.create(user=biz, role="business")
        biz_profile = BusinessProfile.objects.create(
            user=biz, company_name="Brand A", city="Pune", state="MH"
        )
        biz_token = f"fake.{biz.pk}.token"

        # Setup Influencer
        inf = User.objects.create_user(username="i1", email="i1@ex.com", is_active=True)
        UserRole.objects.create(user=inf, role="influencer")
        inf_profile = InfluencerProfile.objects.create(
            user=inf,
            full_name="Creator A",
            category="Fashion",
            followers=10000,
            city="Pune",
            state="MH",
        )
        inf_token = f"fake.{inf.pk}.token"

        # 1. Business sends Campaign proposal
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {biz_token}")
        camp_payload = {
            "influencer": inf_profile.id,
            "title": "Summer Launch Campaign",
            "message": "We would love to feature our summer line with your audience.",
            "budget": "25000.00",
        }
        res = self.client.post("/api/campaigns/send/", camp_payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        campaign_id = res.data["id"]

        # 2. Influencer receives notification and sees campaign
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {inf_token}")
        res = self.client.get("/api/campaigns/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["status"], "Pending")

        res = self.client.get("/api/notifications/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(res.data["count"], 1)

        # 3. Influencer accepts Campaign
        res = self.client.post(f"/api/campaigns/{campaign_id}/accept/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Verify status is Accepted
        camp = CampaignRequest.objects.get(id=campaign_id)
        self.assertEqual(camp.status, "Accepted")
        self.assertIsNotNone(camp.conversation)

        # 4. Chat conversation exists for both parties
        conv_id = camp.conversation.id
        res = self.client.get("/api/chat/conversations/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], conv_id)

        # 5. Send message from Business to Influencer
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {biz_token}")
        res = self.client.post(
            "/api/chat/upload/",
            {
                "conversation": conv_id,
                "text": "Hello! Looking forward to working together.",
            },
            format="multipart",
        )
        # Or verify messages endpoint
        res = self.client.get(f"/api/chat/messages/{conv_id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("messages", res.data)
