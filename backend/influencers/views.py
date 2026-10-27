import secrets

from django.db.models import Q, QuerySet
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated

from accounts.permissions import IsBusinessUser, IsInfluencerUser
from config.media_cleanup import delete_replaced_file
from .models import InfluencerProfile, VerificationAudit
from .serializers import (
    InfluencerRegisterSerializer,
    InfluencerProfileSerializer,
    InfluencerListSerializer,
    VerificationRequestSerializer,
)


class InfluencerRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = InfluencerRegisterSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()

            email_sent = serializer.context.get("email_sent", True)
            message = (
                "Influencer registered successfully! Verification code sent to your email."
                if email_sent
                else (
                    "Influencer registered successfully, but the verification email "
                    "could not be sent. Please use Resend on the next screen."
                )
            )

            return Response(
                {
                    "message": message,
                    "email": serializer.validated_data["email"],
                    "verification_required": True,
                    "email_sent": email_sent,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Logged-in Influencer Profile
class InfluencerProfileView(APIView):
    permission_classes = [IsInfluencerUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        try:
            influencer = InfluencerProfile.objects.get(user=request.user)

            serializer = InfluencerProfileSerializer(influencer)

            return Response(serializer.data)

        except InfluencerProfile.DoesNotExist:
            return Response(
                {"error": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

    def put(self, request):
        return self._update(request)

    def patch(self, request):
        # PATCH accepts multipart/form-data so profile_image can be uploaded.
        return self._update(request)

    def _update(self, request):
        try:
            influencer = InfluencerProfile.objects.get(user=request.user)

            # Remember the previous photo so a replaced one can be removed
            # from storage (keeps S3/local media footprint bounded).
            previous_image_name = influencer.profile_image.name if influencer.profile_image else ""

            serializer = InfluencerProfileSerializer(
                influencer,
                data=request.data,
                partial=True,
            )

            if serializer.is_valid():
                serializer.save()

                delete_replaced_file(
                    old_name=previous_image_name,
                    new_name=influencer.profile_image.name if influencer.profile_image else "",
                )

                return Response(serializer.data)

            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        except InfluencerProfile.DoesNotExist:
            return Response(
                {"error": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )


class InfluencerSearchPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 48


def _filtered_influencers(params) -> QuerySet[InfluencerProfile]:
    """ORM-level discovery filters — never loads the whole table."""
    queryset = InfluencerProfile.objects.select_related("user").order_by("-followers", "id")

    search = (params.get("search") or params.get("q") or "").strip()
    if search:
        queryset = queryset.filter(
            Q(full_name__icontains=search)
            | Q(category__icontains=search)
            | Q(city__icontains=search)
            | Q(state__icontains=search)
        )

    category = (params.get("category") or "").strip()
    if category and category != "all":
        queryset = queryset.filter(category__iexact=category)

    language = (params.get("language") or "").strip()
    if language and language != "all":
        queryset = queryset.filter(language__iexact=language)

    city = (params.get("city") or "").strip()
    if city:
        queryset = queryset.filter(city__icontains=city)

    state = (params.get("state") or "").strip()
    if state:
        queryset = queryset.filter(state__icontains=state)

    min_followers = params.get("min_followers")
    if min_followers not in (None, ""):
        try:
            queryset = queryset.filter(followers__gte=int(min_followers))
        except ValueError:
            pass

    max_followers = params.get("max_followers")
    if max_followers not in (None, ""):
        try:
            queryset = queryset.filter(followers__lte=int(max_followers))
        except ValueError:
            pass

    verified_only = (params.get("verified_only") or "").strip().lower() in {"1", "true", "yes"}
    if verified_only:
        queryset = queryset.filter(is_verified=True)

    return queryset


# Authenticated users can browse influencers (server-side search + pagination)
class InfluencerListView(generics.ListAPIView):
    serializer_class = InfluencerListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = InfluencerSearchPagination

    def get_queryset(self):
        return _filtered_influencers(self.request.query_params)


class InfluencerDetailView(RetrieveAPIView):
    queryset = InfluencerProfile.objects.select_related("user")
    serializer_class = InfluencerProfileSerializer
    permission_classes = [IsAuthenticated]


class VerificationRequestView(APIView):
    """Influencer starts social-account ownership verification.

    Generates a unique code to add to the Instagram bio; an admin then
    approves manually. A URL alone never proves ownership.
    """

    permission_classes = [IsInfluencerUser]

    def get(self, request):
        profile = InfluencerProfile.objects.filter(user=request.user).first()
        if not profile:
            return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {
                "is_verified": profile.is_verified,
                "verification_status": profile.verification_status,
                "verification_code": profile.social_verification_code or "",
                "social_verification_code": profile.social_verification_code or "",
                "instagram_url": profile.instagram or "",
                "submitted_at": profile.verification_submitted_at.isoformat() if profile.verification_submitted_at else None,
                "reviewed_at": profile.verification_reviewed_at.isoformat() if profile.verification_reviewed_at else None,
                "rejection_reason": profile.verification_rejection_reason or "",
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        profile = InfluencerProfile.objects.filter(user=request.user).first()
        if not profile:
            return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)
        if profile.is_verified:
            return Response({"detail": "This account is already verified."}, status=status.HTTP_409_CONFLICT)

        serializer = VerificationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        instagram_url = serializer.validated_data["instagram_url"]
        refresh = bool(request.data.get("refresh", False))

        # Reuse existing code unless none exists or a refresh is explicitly requested
        if profile.social_verification_code and not refresh:
            code = profile.social_verification_code
        else:
            code = f"IH-{secrets.token_hex(3).upper()}"

        profile.social_verification_code = code
        profile.instagram = instagram_url
        profile.verification_status = "Pending"
        profile.verification_submitted_at = timezone.now()
        profile.verification_rejection_reason = ""
        profile.save(
            update_fields=[
                "instagram",
                "social_verification_code",
                "verification_status",
                "verification_submitted_at",
                "verification_rejection_reason",
            ]
        )

        VerificationAudit.objects.create(
            profile=profile,
            action=VerificationAudit.ACTION_SUBMITTED,
        )

        return Response(
            {
                "message": (
                    f"Add the code {code} to your Instagram bio, then an admin will "
                    "confirm ownership and grant your Verified badge."
                ),
                "verification_code": code,
                "social_verification_code": code,
                "instagram_url": profile.instagram,
                "verification_status": profile.verification_status,
                "submitted_at": profile.verification_submitted_at.isoformat(),
            },
            status=status.HTTP_200_OK,
        )