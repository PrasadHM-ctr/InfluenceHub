from django.urls import path

from .views import (
    AdminActivityLogView,
    AdminAnalyticsView,
    AdminBusinessListView,
    AdminCampaignDetailView,
    AdminCampaignListView,
    AdminDashboardView,
    AdminInfluencerListView,
    AdminLoginAuditView,
    AdminNotificationsView,
    AdminSettingsView,
    AdminUserDetailView,
    AdminUserListView,
    AdminVerificationQueueView,
    AdminVerificationReviewView,
)

urlpatterns = [
    path("dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("users/", AdminUserListView.as_view(), name="admin-users"),
    path("users/<int:pk>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("influencers/", AdminInfluencerListView.as_view(), name="admin-influencers"),
    path("businesses/", AdminBusinessListView.as_view(), name="admin-businesses"),
    path("campaigns/", AdminCampaignListView.as_view(), name="admin-campaigns"),
    path("campaigns/<int:pk>/", AdminCampaignDetailView.as_view(), name="admin-campaign-detail"),
    path("verifications/", AdminVerificationQueueView.as_view(), name="admin-verifications"),
    path("verifications/<int:pk>/review/", AdminVerificationReviewView.as_view(), name="admin-verification-review"),
    path("analytics/", AdminAnalyticsView.as_view(), name="admin-analytics"),
    path("activity/", AdminActivityLogView.as_view(), name="admin-activity"),
    path("notifications/", AdminNotificationsView.as_view(), name="admin-notifications"),
    path("settings/", AdminSettingsView.as_view(), name="admin-settings"),
    path("login-audit/", AdminLoginAuditView.as_view(), name="admin-login-audit"),
]
