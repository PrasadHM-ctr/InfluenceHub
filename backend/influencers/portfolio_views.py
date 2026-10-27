"""
Portfolio media management + verification submission for influencers.

Security:
- Only an authenticated user who OWNS an InfluencerProfile may upload/delete
  their portfolio media or submit their profile for verification.
- Ownership is enforced on the backend for every object operation, so an
  influencer can never modify another influencer's media.
"""

from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import InfluencerMedia, InfluencerProfile, VerificationAudit
from .portfolio_serializers import (
    InfluencerMediaCreateSerializer,
    InfluencerMediaSerializer,
)

MAX_PORTFOLIO_IMAGES = 12


def get_own_profile(user):
    """Return the InfluencerProfile owned by this user, or None."""
    return InfluencerProfile.objects.filter(user=user).first()


class IsInfluencerOwner(permissions.BasePermission):
    """Authenticated user who owns an InfluencerProfile (or platform staff)."""

    message = "Only the owning influencer can perform this action."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
            return True
        return InfluencerProfile.objects.filter(user=user).exists()

    def has_object_permission(self, request, view, obj):
        user = request.user
        if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
            return True
        profile = get_own_profile(user)
        return profile is not None and obj.influencer_id == profile.pk


class PortfolioListCreateView(generics.ListCreateAPIView):
    """GET: public list of an influencer's portfolio (?influencer=<profile_id>).
    POST: owning influencer uploads one portfolio image."""

    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsInfluencerOwner()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return InfluencerMediaCreateSerializer
        return InfluencerMediaSerializer

    def get_queryset(self):
        queryset = InfluencerMedia.objects.select_related("influencer")
        influencer_id = self.request.query_params.get("influencer")
        if influencer_id:
            return queryset.filter(influencer_id=influencer_id)
        profile = get_own_profile(self.request.user)
        if profile is None:
            return InfluencerMedia.objects.none()
        return queryset.filter(influencer=profile)

    def perform_create(self, serializer):
        profile = get_own_profile(self.request.user)
        if profile is None:
            raise PermissionDenied("An influencer profile is required.")
        existing = InfluencerMedia.objects.filter(influencer=profile).count()
        if existing >= MAX_PORTFOLIO_IMAGES:
            raise ValidationError(
                {"detail": f"Portfolio is limited to {MAX_PORTFOLIO_IMAGES} images."}
            )
        serializer.save(influencer=profile)


class PortfolioDetailView(generics.RetrieveDestroyAPIView):
    """GET: public single media item.
    DELETE: owning influencer only — also removes the stored S3 object."""

    queryset = InfluencerMedia.objects.select_related("influencer")
    serializer_class = InfluencerMediaSerializer

    def get_permissions(self):
        if self.request.method in ("DELETE", "PUT", "PATCH"):
            return [IsInfluencerOwner()]
        return [permissions.AllowAny()]


class SubmitVerificationView(APIView):
    """Influencer submits their completed profile for owner/admin review.

    Status lives in InfluencerProfile.verification_status ("Pending" /
    "Approved" / "Rejected"). Every transition is recorded in VerificationAudit.
    """

    permission_classes = [IsInfluencerOwner]

    def post(self, request):
        profile = get_own_profile(request.user)
        if profile is None:
            return Response(
                {"detail": "Influencer profile not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        current = (profile.verification_status or "").strip().lower()
        if current == "approved":
            return Response(
                {
                    "detail": "Profile is already verified.",
                    "verification_status": profile.verification_status,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if current == "pending":
            return Response(
                {
                    "detail": "Verification is already pending review.",
                    "verification_status": profile.verification_status,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        profile.verification_status = "Pending"
        profile.save(update_fields=["verification_status"])
        VerificationAudit.objects.create(
            profile=profile, action=VerificationAudit.ACTION_SUBMITTED
        )
        return Response(
            {
                "detail": "Profile submitted for verification review.",
                "verification_status": profile.verification_status,
            },
            status=status.HTTP_200_OK,
        )
