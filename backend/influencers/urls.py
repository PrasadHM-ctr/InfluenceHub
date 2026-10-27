from django.urls import path

from .views import (
    InfluencerDetailView,
    InfluencerRegisterView,
    InfluencerProfileView,
    InfluencerListView,
    VerificationRequestView,
)

urlpatterns = [
    path(
        "influencer/register/",
        InfluencerRegisterView.as_view(),
        name="influencer-register",
    ),

    path(
        "influencer/profile/",
        InfluencerProfileView.as_view(),
        name="influencer-profile",
    ),

    path(
        "influencer/verification/request/",
        VerificationRequestView.as_view(),
        name="influencer-verification-request",
    ),

    path(
        "influencers/",
        InfluencerListView.as_view(),
        name="influencer-list",
    ),
    path(
    "influencers/<int:pk>/",
    InfluencerDetailView.as_view(),
    name="influencer-detail",
),
]
# --- appended: portfolio media + verification submission (owner-panel upgrade) ---
from .portfolio_views import (  # noqa: E402
    PortfolioDetailView,
    PortfolioListCreateView,
    SubmitVerificationView,
)

urlpatterns += [
    path("portfolio/", PortfolioListCreateView.as_view(), name="influencer-portfolio"),
    path("portfolio/<int:pk>/", PortfolioDetailView.as_view(), name="influencer-portfolio-detail"),
    path("verification/submit/", SubmitVerificationView.as_view(), name="influencer-verification-submit"),
]

