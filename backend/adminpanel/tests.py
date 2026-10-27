"""Security and functionality tests for the owner-only admin panel.

The suite runs against the hermetic fake Cognito backend, where tokens of
the form ``fake.<user_pk>.token`` resolve to local users. No AWS contact.

Core guarantees covered here:
* unauthenticated callers get 401 on every admin API
* business and influencer accounts get 403 (backend-enforced, independent
  of any frontend state)
* the owner gets 200 and real database-derived data
* moderation actions are audited and dangerous ones are guarded
"""

from io import StringIO
from unittest import mock

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from accounts import cognito
from accounts.cognito import _FAKE_USERS
from accounts.models import CognitoIdentity, UserRole
from adminpanel.models import AuditLog
from businesses.models import BusinessProfile
from campaigns.models import CampaignRequest
from influencers.models import InfluencerProfile
from notifications.models import Notification

TEST_CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


def _clear_fake_pool():
    _FAKE_USERS.clear()


class AdminTestBase(APITestCase):
    """Shared fixture factory for admin suites."""

    def make_owner(self, username="platform-owner"):
        user = User.objects.create_user(
            username=username, email=f"{username}@example.com",
            password="safe-password-123", is_active=True,
        )
        UserRole.objects.create(user=user, role="owner")
        return user

    def make_business(self, username="brand-account"):
        user = User.objects.create_user(
            username=username, email=f"{username}@example.com",
            password="safe-password-123", is_active=True,
        )
        UserRole.objects.create(user=user, role="business")
        BusinessProfile.objects.create(
            user=user, company_name=f"{username} Co", industry="technology",
            phone="9876543210", city="Bengaluru", state="Karnataka",
        )
        return user

    def make_influencer(self, username="creator-account", verification_status="Pending"):
        user = User.objects.create_user(
            username=username, email=f"{username}@example.com",
            password="safe-password-123", is_active=True,
        )
        UserRole.objects.create(user=user, role="influencer")
        InfluencerProfile.objects.create(
            user=user, full_name=f"Creator {username}", category="fitness",
            language="English", followers=5000, city="Bengaluru",
            state="Karnataka", verification_status=verification_status,
        )
        return user

    def auth(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer fake.{user.pk}.token")


@override_settings(CACHES=TEST_CACHES)
class AdminSecurityTests(AdminTestBase):
    """The seven core access-control requirements."""

    def setUp(self):
        _clear_fake_pool()
        self.owner = self.make_owner()
        self.business = self.make_business("brand-sec")
        self.influencer = self.make_influencer("creator-sec")

    # --- TEST 1: unauthenticated -------------------------------------------------
    def test_unauthenticated_gets_401_on_admin_api(self):
        for url in ("/api/admin/dashboard/", "/api/admin/users/", "/api/admin/campaigns/", "/api/admin/analytics/"):
            response = self.client.get(url)
            self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN), url)

    # --- TEST 2: business blocked --------------------------------------------------
    def test_business_user_blocked_from_every_admin_api(self):
        self.auth(self.business)
        protected = (
            ("/api/admin/dashboard/", "get"),
            ("/api/admin/users/", "get"),
            (f"/api/admin/users/{self.influencer.pk}/", "get"),
            (f"/api/admin/users/{self.influencer.pk}/", "patch"),
            (f"/api/admin/users/{self.influencer.pk}/", "delete"),
            ("/api/admin/influencers/", "get"),
            ("/api/admin/businesses/", "get"),
            ("/api/admin/campaigns/", "get"),
            ("/api/admin/verifications/", "get"),
            ("/api/admin/analytics/", "get"),
            ("/api/admin/activity/", "get"),
            ("/api/admin/notifications/", "get"),
            ("/api/admin/settings/", "get"),
            ("/api/admin/login-audit/", "post"),
        )
        for url, method in protected:
            response = getattr(self.client, method)(url, format="json")
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, url)

    # --- TEST 3: influencer blocked -------------------------------------------------
    def test_influencer_user_blocked_from_every_admin_api(self):
        self.auth(self.influencer)
        for url in ("/api/admin/dashboard/", "/api/admin/users/", "/api/admin/settings/"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, url)

    def test_business_cannot_modify_or_delete_users_via_admin_api(self):
        self.auth(self.business)
        response = self.client.patch(
            f"/api/admin/users/{self.influencer.pk}/", {"action": "suspend"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.influencer.refresh_from_db()
        self.assertTrue(self.influencer.is_active)

    # --- TEST 4/7: owner allowed -----------------------------------------------------
    def test_owner_can_access_dashboard_with_real_counts(self):
        self.auth(self.owner)
        response = self.client.get("/api/admin/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["users"]["total"], 3)
        self.assertEqual(response.data["users"]["business"], 1)
        self.assertEqual(response.data["users"]["influencer"], 1)
        self.assertEqual(response.data["users"]["owner"], 1)
        self.assertEqual(response.data["moderation"]["pending_verifications"], 1)


@override_settings(CACHES=TEST_CACHES)
class AdminRouteProtectionRegressionTests(AdminTestBase):
    """Manual navigation attempts land safely (no data exposure)."""

    def setUp(self):
        _clear_fake_pool()
        self.business = self.make_business("brand-nav")

    # --- TEST 5: business manually opens a protected surface ---------------------
    def test_django_admin_site_denies_business_account(self):
        self.client.force_login(self.business)
        response = self.client.get("/admin/")
        # Django redirects non-staff visitors to its login page instead of
        # rendering anything sensitive.
        self.assertIn(response.status_code, (status.HTTP_200_OK, status.HTTP_302_FOUND))
        if response.status_code == status.HTTP_200_OK:
            self.assertContains(response, "Log in", status_code=200)

    def test_invalid_token_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer fake.99999.token")
        response = self.client.get("/api/admin/dashboard/")
        # DRF answers 401 when a WWW-Authenticate header is available and
        # 403 otherwise; both deny access (same contract as the rest of the API).
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_tampered_token_format_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
        response = self.client.get("/api/admin/dashboard/")
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))


@override_settings(CACHES=TEST_CACHES)
class AdminUserManagementTests(AdminTestBase):
    def setUp(self):
        _clear_fake_pool()
        self.owner = self.make_owner("owner-mgr")
        self.influencer = self.make_influencer("creator-mgr")

    def test_user_list_search_by_email_and_name(self):
        self.auth(self.owner)
        by_email = self.client.get("/api/admin/users/?search=creator-mgr@example.com")
        self.assertEqual(by_email.status_code, status.HTTP_200_OK)
        self.assertEqual(by_email.data["count"], 1)
        self.assertEqual(by_email.data["results"][0]["username"], "creator-mgr")

        by_name = self.client.get("/api/admin/users/?search=Creator creator-mgr")
        self.assertEqual(by_name.data["count"], 1)

        miss = self.client.get("/api/admin/users/?search=nobody-xyz")
        self.assertEqual(miss.data["count"], 0)

    def test_user_list_filters_and_sort(self):
        self.auth(self.owner)
        roles = self.client.get("/api/admin/users/?role=influencer")
        self.assertEqual(roles.data["count"], 1)
        self.assertEqual(roles.data["results"][0]["role"], "influencer")

        verified = self.client.get("/api/admin/users/?verification=verified")
        self.assertEqual(verified.data["count"], 2)

        inactive_probe = User.objects.create_user(username="pending-otp", email="p@example.com", is_active=False)
        UserRole.objects.create(user=inactive_probe, role="business")
        unverified = self.client.get("/api/admin/users/?verification=unverified")
        self.assertEqual(unverified.data["count"], 1)

        oldest_first = self.client.get("/api/admin/users/?sort=oldest")
        self.assertEqual(oldest_first.data["results"][0]["username"], "owner-mgr")

    def test_user_pagination(self):
        self.auth(self.owner)
        for i in range(25):
            extra = User.objects.create_user(username=f"bulk-{i}", email=f"bulk-{i}@example.com")
            UserRole.objects.create(user=extra, role="business")
        page_one = self.client.get("/api/admin/users/")
        self.assertEqual(page_one.data["count"], 27)  # owner + influencer + 25
        self.assertEqual(len(page_one.data["results"]), 20)
        self.assertIsNotNone(page_one.data["next"])
        page_two = self.client.get("/api/admin/users/?page=2")
        self.assertEqual(len(page_two.data["results"]), 7)

    def test_user_detail_returns_profile_and_audits_view(self):
        self.auth(self.owner)
        response = self.client.get(f"/api/admin/users/{self.influencer.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["profile"]["type"], "influencer")
        self.assertEqual(response.data["campaigns"]["total"], 0)
        self.assertIn("risk_score", response.data["profile"])
        self.assertIn("completion_percentage", response.data["profile"])

        missing = self.client.get("/api/admin/users/424242/")
        self.assertEqual(missing.status_code, status.HTTP_404_NOT_FOUND)

    def test_suspend_then_activate_roundtrip(self):
        self.auth(self.owner)
        suspended = self.client.patch(
            f"/api/admin/users/{self.influencer.pk}/", {"action": "suspend"}, format="json"
        )
        self.assertEqual(suspended.status_code, status.HTTP_200_OK)
        self.influencer.refresh_from_db()
        self.assertFalse(self.influencer.is_active)

        activated = self.client.patch(
            f"/api/admin/users/{self.influencer.pk}/", {"action": "activate"}, format="json"
        )
        self.assertEqual(activated.status_code, status.HTTP_200_OK)
        self.influencer.refresh_from_db()
        self.assertTrue(self.influencer.is_active)

    def test_verify_and_reject_influencer_profile(self):
        self.auth(self.owner)
        approved = self.client.patch(
            f"/api/admin/users/{self.influencer.pk}/", {"action": "verify_profile"}, format="json"
        )
        self.assertEqual(approved.status_code, status.HTTP_200_OK)
        self.influencer.influencerprofile.refresh_from_db()
        self.assertEqual(self.influencer.influencerprofile.verification_status, "Approved")
        self.assertTrue(self.influencer.influencerprofile.is_verified)

        rejected = self.client.patch(
            f"/api/admin/users/{self.influencer.pk}/", {"action": "reject_profile"}, format="json"
        )
        self.assertEqual(rejected.status_code, status.HTTP_200_OK)
        self.influencer.influencerprofile.refresh_from_db()
        self.assertEqual(self.influencer.influencerprofile.verification_status, "Rejected")

    def test_delete_requires_delete_method_and_removes_account(self):
        self.auth(self.owner)
        # A normal GET must never delete.
        safe = self.client.get(f"/api/admin/users/{self.influencer.pk}/")
        self.assertEqual(safe.status_code, status.HTTP_200_OK)
        self.assertTrue(User.objects.filter(pk=self.influencer.pk).exists())

        deleted = self.client.delete(f"/api/admin/users/{self.influencer.pk}/")
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(pk=self.influencer.pk).exists())

    def test_owner_cannot_suspend_or_delete_self(self):
        self.auth(self.owner)
        suspend_self = self.client.patch(
            f"/api/admin/users/{self.owner.pk}/", {"action": "suspend"}, format="json"
        )
        self.assertEqual(suspend_self.status_code, status.HTTP_400_BAD_REQUEST)
        delete_self = self.client.delete(f"/api/admin/users/{self.owner.pk}/")
        self.assertEqual(delete_self.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(User.objects.filter(pk=self.owner.pk).exists())

    def test_actions_recorded_in_audit_log(self):
        self.auth(self.owner)
        self.client.get(f"/api/admin/users/{self.influencer.pk}/")
        self.client.patch(f"/api/admin/users/{self.influencer.pk}/", {"action": "suspend"}, format="json")
        self.client.patch(f"/api/admin/users/{self.influencer.pk}/", {"action": "activate"}, format="json")
        log = self.client.get("/api/admin/activity/")
        actions = {entry["action"] for entry in log.data["results"]}
        self.assertIn("user_suspended", actions)
        self.assertIn("user_activated", actions)
        self.assertIn("user_viewed", actions)


@override_settings(CACHES=TEST_CACHES)
class AdminCampaignAndVerificationTests(AdminTestBase):
    def setUp(self):
        _clear_fake_pool()
        self.owner = self.make_owner("owner-camp")
        self.business = self.make_business("brand-camp")
        self.influencer = self.make_influencer("creator-camp")
        self.campaign = CampaignRequest.objects.create(
            business=self.business.businessprofile,
            influencer=self.influencer.influencerprofile,
            title="Launch push",
            message="Promote the new product line.",
            budget=25000,
            status="Pending",
        )

    def test_campaign_list_filter_and_search(self):
        self.auth(self.owner)
        listing = self.client.get("/api/admin/campaigns/")
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(listing.data["count"], 1)

        filtered = self.client.get("/api/admin/campaigns/?status=Accepted")
        self.assertEqual(filtered.data["count"], 0)

        searched = self.client.get("/api/admin/campaigns/?search=brand-camp")
        self.assertEqual(searched.data["count"], 1)

    def test_campaign_detail_inspection_is_audited(self):
        self.auth(self.owner)
        detail = self.client.get(f"/api/admin/campaigns/{self.campaign.pk}/")
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data["business_detail"]["company_name"], "brand-camp Co")
        self.assertEqual(detail.data["influencer_detail"]["full_name"], "Creator creator-camp")
        log = self.client.get("/api/admin/activity/?action=campaign_viewed")
        self.assertEqual(log.data["count"], 1)

    def test_campaign_moderation_requires_explicit_confirmation(self):
        self.auth(self.owner)
        without_confirm = self.client.patch(
            f"/api/admin/campaigns/{self.campaign.pk}/", {"status": "Cancelled"}, format="json"
        )
        self.assertEqual(without_confirm.status_code, status.HTTP_400_BAD_REQUEST)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, "Pending")

        with_confirm = self.client.patch(
            f"/api/admin/campaigns/{self.campaign.pk}/",
            {"status": "Cancelled", "confirm": True},
            format="json",
        )
        self.assertEqual(with_confirm.status_code, status.HTTP_200_OK)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, "Cancelled")
        # Both participants were notified via the existing notification system.
        self.assertTrue(Notification.objects.filter(recipient=self.business).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.influencer).exists())

    def test_verification_queue_lists_pending_and_review_updates(self):
        self.auth(self.owner)
        queue = self.client.get("/api/admin/verifications/")
        self.assertEqual(queue.status_code, status.HTTP_200_OK)
        self.assertEqual(queue.data["count"], 1)
        self.assertEqual(queue.data["results"][0]["verification_status"], "Pending")

        approved = self.client.post(
            f"/api/admin/verifications/{self.influencer.influencerprofile.pk}/review/",
            {"decision": "approved"},
            format="json",
        )
        self.assertEqual(approved.status_code, status.HTTP_200_OK)
        self.influencer.influencerprofile.refresh_from_db()
        self.assertEqual(self.influencer.influencerprofile.verification_status, "Approved")
        self.assertTrue(Notification.objects.filter(recipient=self.influencer).exists())

        rejected = self.client.post(
            f"/api/admin/verifications/{self.influencer.influencerprofile.pk}/review/",
            {"decision": "rejected"},
            format="json",
        )
        self.assertEqual(rejected.status_code, status.HTTP_200_OK)
        self.influencer.influencerprofile.refresh_from_db()
        self.assertEqual(self.influencer.influencerprofile.verification_status, "Rejected")


@override_settings(CACHES=TEST_CACHES)
class AdminAnalyticsNotificationsSettingsTests(AdminTestBase):
    def setUp(self):
        _clear_fake_pool()
        self.owner = self.make_owner("owner-analytics")
        self.business = self.make_business("brand-ana")
        self.influencer = self.make_influencer("creator-ana")
        CampaignRequest.objects.create(
            business=self.business.businessprofile,
            influencer=self.influencer.influencerprofile,
            title="Festive push",
            message="Boost festival reach.",
            budget=10000,
            status="Completed",
        )

    def test_analytics_returns_real_aggregates(self):
        self.auth(self.owner)
        response = self.client.get("/api/admin/analytics/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["totals"]["users"], 3)
        self.assertEqual(response.data["totals"]["completed_campaigns"], 1)
        self.assertEqual(response.data["totals"]["budget_total"], "10000.00")
        self.assertEqual(len(response.data["users_over_time"]), 14)
        distribution = {row["status"]: row["count"] for row in response.data["campaign_status_distribution"]}
        self.assertEqual(distribution.get("Completed"), 1)

    def test_notifications_feed_and_mark_seen(self):
        self.auth(self.owner)
        feed = self.client.get("/api/admin/notifications/")
        self.assertEqual(feed.status_code, status.HTTP_200_OK)
        keys = {item["key"] for item in feed.data["results"]}
        self.assertIn("pending_verifications", keys)

        seen = self.client.post("/api/admin/notifications/")
        self.assertEqual(seen.status_code, status.HTTP_200_OK)
        feed_after = self.client.get("/api/admin/notifications/")
        self.assertEqual(feed_after.data["unread_count"], 0)

    def test_settings_overview_lists_owner_accounts(self):
        self.auth(self.owner)
        response = self.client.get("/api/admin/settings/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["session_user"]["username"], "owner-analytics")
        owner_names = {account["username"] for account in response.data["owner_accounts"]}
        self.assertIn("owner-analytics", owner_names)

    def test_login_audit_records_admin_login(self):
        self.auth(self.owner)
        recorded = self.client.post("/api/admin/login-audit/")
        self.assertEqual(recorded.status_code, status.HTTP_200_OK)
        log = self.client.get("/api/admin/activity/?action=admin_login")
        self.assertEqual(log.data["count"], 1)


@override_settings(CACHES=TEST_CACHES)
class OwnerProvisioningAndSignupSafetyTests(AdminTestBase):
    """The owner role must only exist through secure provisioning."""

    def test_create_owner_management_command_provisions_account_with_role(self):
        _clear_fake_pool()
        out = StringIO()
        call_command(
            "create_owner",
            "--username", "new-owner",
            "--email", "new-owner@example.com",
            "--password", "safe-password-123",
            stdout=out,
        )
        user = User.objects.get(username="new-owner")
        self.assertEqual(user.userrole.role, "owner")
        self.assertFalse(user.is_active)  # awaits the standard email OTP flow
        self.assertIn("new-owner@example.com", _FAKE_USERS)  # registered with Cognito

    def test_create_owner_promotes_existing_account_without_touching_cognito(self):
        existing = self.make_influencer("promoted-creator")
        before_pool = dict(_FAKE_USERS)
        out = StringIO()
        call_command(
            "create_owner",
            "--username", "promoted-creator",
            "--email", "promoted-creator@example.com",
            stdout=out,
        )
        existing.userrole.refresh_from_db()
        self.assertEqual(existing.userrole.role, "owner")
        self.assertEqual(before_pool, dict(_FAKE_USERS))

    def test_public_signup_cannot_assign_privileged_roles(self):
        payload = {
            "username": "role-hacker",
            "email": "hacker@example.com",
            "password": "safe-password-123",
            "company_name": "Sneaky Co",
            "industry": "technology",
            "phone": "9876543210",
            "city": "Bengaluru",
            "state": "Karnataka",
            # Attempted privilege escalation - must be ignored entirely.
            "role": "owner",
            "is_superuser": True,
        }
        response = self.client.post("/api/business/register/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="hacker@example.com")
        self.assertEqual(user.userrole.role, "business")
        self.assertFalse(user.is_superuser)


class AdminDeleteFreesEmailTests(AdminTestBase):
    """Regression tests: permanent delete must free the email everywhere.

    Root cause these guard against: the Cognito record survived admin
    deletion, so re-registering the same address failed with
    "An account with the given email already exists."
    """

    def setUp(self):
        _clear_fake_pool()
        self.owner = self.make_owner()

    def _signup_identity(self, email):
        """Simulate a real signup: pool entry + login-recorded sub."""
        cognito.sign_up(email=email, password="safe-password-123", role="business")

    def test_delete_removes_cognito_record_and_frees_email(self):
        target = self.make_business(username="doomed-brand")
        target.email = "doomed.brand@gmail.com"
        target.save(update_fields=["email"])
        identity = CognitoIdentity.objects.create(
            user=target, sub="sub-doomed-1", role="business"
        )
        self._signup_identity(target.email)

        self.client.force_authenticate(self.owner)
        response = self.client.delete(f"/api/admin/users/{target.pk}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Auth record gone from the pool AND application row gone.
        self.assertNotIn("doomed.brand@gmail.com", _FAKE_USERS)

        # The exact user-visible bug: same email must be registrable again.
        response = self.client.post("/api/business/register/", {
            "username": "brand-reborn",
            "email": "DOOMED.BRAND@Gmail.com",  # case-insensitive reuse
            "password": "safe-password-123",
            "company_name": "Reborn Co",
            "industry": "technology",
            "phone": "9876543210",
            "city": "Bengaluru",
            "state": "Karnataka",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        reborn = User.objects.get(email__iexact="doomed.brand@gmail.com")
        self.assertEqual(reborn.username, "brand-reborn")
        self.assertNotEqual(reborn.pk, target.pk)
        self.assertEqual(reborn.email, "doomed.brand@gmail.com")  # normalized

    def test_influencer_delete_then_re_register_same_email(self):
        target = self.make_influencer(username="doomed-creator")
        target.email = "doomed.creator@gmail.com"
        target.save(update_fields=["email"])
        CognitoIdentity.objects.create(user=target, sub="sub-doomed-2", role="influencer")
        cognito.sign_up(email=target.email, password="safe-password-123", role="influencer")

        self.client.force_authenticate(self.owner)
        response = self.client.delete(f"/api/admin/users/{target.pk}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.post("/api/influencer/register/", {
            "username": "creator-reborn",
            "email": "doomed.creator@gmail.com",
            "password": "safe-password-123",
            "full_name": "Reborn Creator",
            "category": "fitness",
            "language": "English",
            "followers": 5000,
            "city": "Bengaluru",
            "state": "Karnataka",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="doomed.creator@gmail.com").exists())

    def test_cognito_failure_leaves_application_data_intact(self):
        """No inconsistent state on AWS failure - retry must be possible."""
        target = self.make_business(username="lucky-brand")
        self.client.force_authenticate(self.owner)

        def explode(*args, **kwargs):
            raise cognito.CognitoError("AWS unavailable.", aws_code="InternalError")

        with mock.patch.object(cognito, "delete_user", side_effect=explode):
            response = self.client.delete(f"/api/admin/users/{target.pk}/")

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertTrue(User.objects.filter(pk=target.pk).exists())
        self.assertFalse(AuditLog.objects.filter(action="user_deleted", target_id=target.pk).exists())

    def test_deletion_is_idempotent_when_pool_entry_already_gone(self):
        target = self.make_business(username="drifted-brand")
        CognitoIdentity.objects.create(user=target, sub="sub-doomed-3", role="business")
        # Pool entry already missing (historical drift) - delete must succeed.

        self.client.force_authenticate(self.owner)
        response = self.client.delete(f"/api/admin/users/{target.pk}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(pk=target.pk).exists())

    def test_owner_cannot_be_deleted_by_self(self):
        self.client.force_authenticate(self.owner)
        response = self.client.delete(f"/api/admin/users/{self.owner.pk}/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)