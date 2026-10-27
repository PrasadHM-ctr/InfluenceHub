from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsBusinessUser, IsInfluencerUser
from businesses.models import BusinessProfile
from influencers.models import InfluencerProfile
from notifications.services import notify, notify_many

from .models import CampaignRequest
from .serializers import CampaignSerializer


class CampaignListView(generics.ListAPIView):
    """Campaign list / history for the signed-in account.

    Optional `?status=` filter supports the campaign-history views. Existing
    response shape is unchanged when no filter is supplied.
    """

    serializer_class = CampaignSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Business sees campaigns it sent
        try:
            business = BusinessProfile.objects.get(user=user)
            queryset = CampaignRequest.objects.filter(business=business).select_related("conversation").order_by("-created_at")
        except BusinessProfile.DoesNotExist:
            # Influencer sees campaigns received
            try:
                influencer = InfluencerProfile.objects.get(user=user)
                queryset = CampaignRequest.objects.filter(influencer=influencer).select_related("conversation").order_by("-created_at")
            except InfluencerProfile.DoesNotExist:
                return CampaignRequest.objects.none()

        status_filter = self.request.query_params.get("status", "").strip()
        if status_filter and status_filter != "all":
            valid = {choice for choice, _ in CampaignRequest.STATUS_CHOICES}
            if status_filter not in valid:
                raise ValidationError({"status": f"Unknown status '{status_filter}'."})
            queryset = queryset.filter(status=status_filter)

        return queryset


class CampaignCreateView(generics.CreateAPIView):
    serializer_class = CampaignSerializer
    permission_classes = [IsBusinessUser]
    # Multipart lets a brief image/PDF be attached to the proposal.
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def perform_create(self, serializer):
        business = BusinessProfile.objects.get(user=self.request.user)
        campaign = serializer.save(business=business)

        notify(
            recipient=campaign.influencer.user,
            notification_type="campaign_new",
            title="New campaign request",
            message=f"{business.company_name} sent you a new campaign: “{campaign.title}”.",
            link="/influencer/dashboard",
        )


def _decide_campaign(request, pk, target_status: str, success_message: str):
    """Shared ownership + transition logic for accept/reject/complete/cancel."""
    campaign = get_object_or_404(
        CampaignRequest.objects.select_related("business", "influencer", "business__user", "influencer__user"),
        id=pk,
    )

    if hasattr(request.user, "businessprofile"):
        if campaign.business_id != request.user.businessprofile.id:
            return Response(
                {"detail": "You do not have permission to modify this campaign."},
                status=status.HTTP_403_FORBIDDEN,
            )
        allowed = {
            "Cancelled": {"Pending"},
            "Completed": {"Accepted"},
        }
    elif hasattr(request.user, "influencerprofile"):
        if campaign.influencer_id != request.user.influencerprofile.id:
            return Response(
                {"detail": "You do not have permission to modify this campaign."},
                status=status.HTTP_403_FORBIDDEN,
            )
        allowed = {
            "Accepted": {"Pending"},
            "Rejected": {"Pending"},
        }
    else:
        return Response({"detail": "Unknown account type."}, status=status.HTTP_403_FORBIDDEN)

    if campaign.status not in allowed.get(target_status, set()):
        raise ValidationError({"detail": "This campaign request has already been decided."})

    campaign.status = target_status
    campaign.save(update_fields=["status", "updated_at"])

    _notify_status_change(campaign, target_status)

    return Response(
        {
            "message": success_message,
            "campaign": CampaignSerializer(campaign, context={"request": request}).data,
        },
        status=status.HTTP_200_OK,
    )


def _notify_status_change(campaign: CampaignRequest, new_status: str) -> None:
    business_user = campaign.business.user
    influencer_user = campaign.influencer.user
    title = campaign.title

    if new_status == "Accepted":
        notify(
            recipient=business_user,
            notification_type="campaign_accepted",
            title="Campaign accepted",
            message=f"{campaign.influencer.full_name} accepted your campaign “{title}”. A conversation is now open.",
            link="/business/messages",
        )
    elif new_status == "Rejected":
        notify(
            recipient=business_user,
            notification_type="campaign_rejected",
            title="Campaign declined",
            message=f"{campaign.influencer.full_name} declined your campaign “{title}”.",
            link="/business/dashboard",
        )
    elif new_status == "Completed":
        notify(
            recipient=business_user,
            notification_type="campaign_completed",
            title="Campaign completed",
            message=f"The campaign “{title}” has been marked as completed.",
            link="/business/dashboard",
        )
        notify(
            recipient=influencer_user,
            notification_type="campaign_completed",
            title="Campaign completed",
            message=f"The campaign “{title}” has been marked as completed.",
            link="/influencer/dashboard",
        )
    elif new_status == "Cancelled":
        notify(
            recipient=influencer_user,
            notification_type="campaign_cancelled",
            title="Campaign cancelled",
            message=f"{campaign.business.company_name} cancelled the campaign “{title}”.",
            link="/influencer/dashboard",
        )


class AcceptCampaignView(APIView):
    permission_classes = [IsInfluencerUser]

    def post(self, request, pk):
        return _decide_campaign(request, pk, "Accepted", "Campaign Accepted")


class RejectCampaignView(APIView):
    permission_classes = [IsInfluencerUser]

    def post(self, request, pk):
        return _decide_campaign(request, pk, "Rejected", "Campaign Rejected")


class CompleteCampaignView(APIView):
    """Business marks an accepted campaign as completed."""

    permission_classes = [IsBusinessUser]

    def post(self, request, pk):
        return _decide_campaign(request, pk, "Completed", "Campaign Completed")


class CancelCampaignView(APIView):
    """Business cancels a still-pending campaign."""

    permission_classes = [IsBusinessUser]

    def post(self, request, pk):
        return _decide_campaign(request, pk, "Cancelled", "Campaign Cancelled")