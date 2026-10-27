from django.test import TestCase, override_settings

# Create your tests here.
from rest_framework import status
from rest_framework.test import APITestCase

from businesses.models import BusinessProfile
from campaigns.models import CampaignRequest
from influencers.models import InfluencerProfile
from accounts.models import EmailVerificationCode
from accounts.cognito import FAKE_CONFIRM_CODE


# Throttling reads the default cache; use in-memory cache so tests do not
# require a running Redis instance (same convention as chat.tests).
TEST_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "campaign-tests",
    }
}


@override_settings(CACHES=TEST_CACHES)
class MarketplaceFlowTests(APITestCase):
    def setUp(self):
        # The fake Cognito pool is module-global; keep tests independent.
        from accounts.cognito import _FAKE_USERS

        _FAKE_USERS.clear()
        self.business = self._register_business("brand-one")
        self.other_business = self._register_business("brand-two")
        self.influencer = self._register_influencer("creator-one")

    def _verify_email(self, email):
        """Complete the email-verification step of the real signup flow."""
        response = self.client.post("/api/verify-email/", {"email": email, "code": FAKE_CONFIRM_CODE}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def _register_business(self, username):
        response = self.client.post(
            "/api/business/register/",
            {
                "username": username,
                "email": f"{username}@example.com",
                "password": "safe-password-123",
                "company_name": f"{username} company",
                "industry": "Fashion",
                "phone": "1234567890",
                "city": "Mumbai",
                "state": "Maharashtra",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self._verify_email(f"{username}@example.com")
        return BusinessProfile.objects.get(user__username=username)

    def _register_influencer(self, username):
        response = self.client.post(
            "/api/influencer/register/",
            {
                "username": username,
                "email": f"{username}@example.com",
                "password": "safe-password-123",
                "full_name": "Creator One",
                "category": "Lifestyle",
                "language": "English",
                "followers": 12000,
                "city": "Delhi",
                "state": "Delhi",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self._verify_email(f"{username}@example.com")
        return InfluencerProfile.objects.get(user__username=username)

    def _authenticate(self, username):
        response = self.client.post(
            "/api/login/",
            {"username": username, "password": "safe-password-123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return response.data

    def test_business_can_find_creator_send_request_and_see_own_dashboard(self):
        tokens = self._authenticate("brand-one")
        self.assertEqual(tokens["role"], "business")

        creators = self.client.get("/api/influencers/")
        self.assertEqual(creators.status_code, status.HTTP_200_OK)
        self.assertEqual(creators.data["results"][0]["id"], self.influencer.id)

        request = self.client.post(
            "/api/campaigns/send/",
            {
                "influencer": self.influencer.id,
                "title": "Autumn launch",
                "message": "Create one short video and two story posts for our launch.",
                "budget": "25000.00",
            },
            format="json",
        )
        self.assertEqual(request.status_code, status.HTTP_201_CREATED)
        self.assertEqual(request.data["business"], self.business.id)
        self.assertEqual(request.data["influencer_name"], self.influencer.full_name)

        dashboard = self.client.get("/api/business/dashboard/")
        self.assertEqual(dashboard.status_code, status.HTTP_200_OK)
        self.assertEqual(dashboard.data, {"total_campaigns": 1, "pending": 1, "accepted": 0, "rejected": 0, "completed": 0, "cancelled": 0})

        self._authenticate("brand-two")
        dashboard = self.client.get("/api/business/dashboard/")
        self.assertEqual(dashboard.data["total_campaigns"], 0)
        self.assertEqual(self.client.get("/api/campaigns/").data, [])

    def test_influencer_receives_and_can_decide_only_own_request(self):
        self._authenticate("brand-one")
        campaign = self.client.post(
            "/api/campaigns/send/",
            {
                "influencer": self.influencer.id,
                "title": "Product video",
                "message": "Please make a detailed product review video.",
                "budget": "15000.00",
            },
            format="json",
        )
        campaign_id = campaign.data["id"]

        tokens = self._authenticate("creator-one")
        self.assertEqual(tokens["role"], "influencer")
        inbox = self.client.get("/api/campaigns/")
        self.assertEqual(inbox.status_code, status.HTTP_200_OK)
        self.assertEqual(inbox.data[0]["id"], campaign_id)

        accepted = self.client.post(f"/api/campaigns/{campaign_id}/accept/")
        self.assertEqual(accepted.status_code, status.HTTP_200_OK)
        self.assertEqual(accepted.data["campaign"]["status"], "Accepted")
        self.assertEqual(CampaignRequest.objects.get(id=campaign_id).status, "Accepted")

        decided_again = self.client.post(f"/api/campaigns/{campaign_id}/reject/")
        self.assertEqual(decided_again.status_code, status.HTTP_400_BAD_REQUEST)

    def test_influencer_cannot_browse_creators_or_send_campaigns(self):
        self._authenticate("creator-one")
        self.assertEqual(self.client.get("/api/influencers/").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            self.client.post(
                "/api/campaigns/send/",
                {
                    "influencer": self.influencer.id,
                    "title": "Invalid request",
                    "message": "This request should be rejected by the server.",
                    "budget": "5000.00",
                },
                format="json",
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_local_frontend_origins_are_allowed(self):
        response = self.client.options(
            "/api/influencers/",
            HTTP_ORIGIN="http://127.0.0.1:3001",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["access-control-allow-origin"], "http://127.0.0.1:3001")
