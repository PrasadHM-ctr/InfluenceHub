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

    # ------------------------------------------------------------------
    # Original tests (unchanged)
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # New tests — Bug #1 regression and permission boundary cases
    # ------------------------------------------------------------------

    def test_unauthenticated_user_cannot_create_campaign(self):
        """Missing JWT must return 401 or 403, not 200 or 500."""
        self.client.credentials()  # clear auth
        r = self.client.post(
            "/api/campaigns/send/",
            {
                "influencer": self.influencer.id,
                "title": "No-auth attempt",
                "message": "This should fail without a token.",
                "budget": "1000.00",
            },
            format="json",
        )
        self.assertIn(r.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_unauthenticated_user_cannot_list_campaigns(self):
        """Campaign list must also require authentication."""
        self.client.credentials()
        r = self.client.get("/api/campaigns/")
        self.assertIn(r.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_business_cannot_accept_campaign(self):
        """
        Bug #1 boundary: the accept endpoint is IsInfluencerUser only.
        A business that calls accept/reject gets 403 with the correct message.
        This is the EXACT error the user sees when the role is stale.
        """
        self._authenticate("brand-one")
        campaign = self.client.post(
            "/api/campaigns/send/",
            {
                "influencer": self.influencer.id,
                "title": "Business accept attempt",
                "message": "Business trying to accept its own campaign.",
                "budget": "5000.00",
            },
            format="json",
        )
        campaign_id = campaign.data["id"]

        # Stay authenticated as business and try to accept
        r = self.client.post(f"/api/campaigns/{campaign_id}/accept/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
        # Confirm the exact permission message that the frontend would display
        self.assertEqual(r.data.get("detail"), "Only influencer accounts can perform this action.")

    def test_business_cannot_reject_campaign(self):
        """Same boundary check for the reject endpoint."""
        self._authenticate("brand-one")
        campaign = self.client.post(
            "/api/campaigns/send/",
            {
                "influencer": self.influencer.id,
                "title": "Business reject attempt",
                "message": "Business trying to reject its own campaign.",
                "budget": "5000.00",
            },
            format="json",
        )
        r = self.client.post(f"/api/campaigns/{campaign.data['id']}/reject/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_business_can_cancel_pending_campaign(self):
        """A business must be able to cancel a campaign it sent while Pending."""
        self._authenticate("brand-one")
        campaign = self.client.post(
            "/api/campaigns/send/",
            {
                "influencer": self.influencer.id,
                "title": "Cancel test",
                "message": "Business will cancel this proposal.",
                "budget": "8000.00",
            },
            format="json",
        )
        campaign_id = campaign.data["id"]
        r = self.client.post(f"/api/campaigns/{campaign_id}/cancel/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(CampaignRequest.objects.get(id=campaign_id).status, "Cancelled")

    def test_business_can_mark_accepted_campaign_completed(self):
        """After the influencer accepts, the business can mark it completed."""
        self._authenticate("brand-one")
        campaign = self.client.post(
            "/api/campaigns/send/",
            {
                "influencer": self.influencer.id,
                "title": "Complete test",
                "message": "Creator will accept, then brand marks complete.",
                "budget": "20000.00",
            },
            format="json",
        )
        campaign_id = campaign.data["id"]

        # Influencer accepts
        self._authenticate("creator-one")
        self.assertEqual(
            self.client.post(f"/api/campaigns/{campaign_id}/accept/").status_code,
            status.HTTP_200_OK,
        )

        # Business marks complete
        self._authenticate("brand-one")
        r = self.client.post(f"/api/campaigns/{campaign_id}/complete/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(CampaignRequest.objects.get(id=campaign_id).status, "Completed")

    def test_business_cannot_manage_another_business_campaign(self):
        """A different business account must not be able to cancel another's campaign."""
        self._authenticate("brand-one")
        campaign = self.client.post(
            "/api/campaigns/send/",
            {
                "influencer": self.influencer.id,
                "title": "Cross-tenant test",
                "message": "Brand two must not touch this.",
                "budget": "12000.00",
            },
            format="json",
        )
        campaign_id = campaign.data["id"]

        # Log in as brand-two and attempt to cancel brand-one's campaign
        self._authenticate("brand-two")
        r = self.client.post(f"/api/campaigns/{campaign_id}/cancel/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_campaign_with_invalid_influencer_id_returns_400(self):
        """Sending a campaign to a non-existent influencer must return 400."""
        self._authenticate("brand-one")
        r = self.client.post(
            "/api/campaigns/send/",
            {
                "influencer": 999999,  # does not exist
                "title": "Ghost influencer",
                "message": "Targeting a non-existent profile.",
                "budget": "5000.00",
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_campaign_with_missing_required_fields_returns_400(self):
        """Malformed payload (missing title and message) must return 400."""
        self._authenticate("brand-one")
        r = self.client.post(
            "/api/campaigns/send/",
            {"influencer": self.influencer.id, "budget": "5000.00"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_campaign_send_creates_two_records(self):
        """
        There is no unique constraint preventing a business from sending two
        proposals to the same influencer — this is intentional. Verify both
        are created and that the IDs are distinct.
        """
        self._authenticate("brand-one")
        payload = {
            "influencer": self.influencer.id,
            "title": "First proposal",
            "message": "Summer collection promotion.",
            "budget": "10000.00",
        }
        r1 = self.client.post("/api/campaigns/send/", payload, format="json")
        r2 = self.client.post("/api/campaigns/send/", {**payload, "title": "Second proposal"}, format="json")
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(r1.data["id"], r2.data["id"])
        self.assertEqual(
            CampaignRequest.objects.filter(business=self.business, influencer=self.influencer).count(),
            2,
        )

    def test_campaign_list_status_filter_valid(self):
        """?status=Pending filter must return only pending campaigns."""
        self._authenticate("brand-one")
        self.client.post(
            "/api/campaigns/send/",
            {
                "influencer": self.influencer.id,
                "title": "Filter test",
                "message": "This will be filtered by status.",
                "budget": "7000.00",
            },
            format="json",
        )
        r = self.client.get("/api/campaigns/?status=Pending")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(all(c["status"] == "Pending" for c in r.data))

    def test_campaign_list_status_filter_invalid(self):
        """An unknown status value must return 400."""
        self._authenticate("brand-one")
        r = self.client.get("/api/campaigns/?status=INVALID_STATUS")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_influencer_permission_error_message_matches_constant(self):
        """
        The backend permission message 'Only influencer accounts can perform
        this action.' is what the frontend displays when a business user
        (due to a stale localStorage role) calls an influencer-only endpoint.
        Confirm the exact string so any change in the permission class is caught.
        """
        from accounts.permissions import IsInfluencerUser
        self.assertEqual(
            IsInfluencerUser.message,
            "Only influencer accounts can perform this action.",
        )
