from django.urls import path

from .views import (
    CampaignListView,
    CampaignCreateView,
    AcceptCampaignView,
    RejectCampaignView,
    CompleteCampaignView,
    CancelCampaignView,
)

urlpatterns = [
    path("campaigns/", CampaignListView.as_view()),
    path("campaigns/send/", CampaignCreateView.as_view()),
    path("campaigns/<int:pk>/accept/", AcceptCampaignView.as_view()),
    path("campaigns/<int:pk>/reject/", RejectCampaignView.as_view()),
    path("campaigns/<int:pk>/complete/", CompleteCampaignView.as_view()),
    path("campaigns/<int:pk>/cancel/", CancelCampaignView.as_view()),
]