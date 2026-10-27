from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny

from campaigns.models import CampaignRequest
from accounts.permissions import IsBusinessUser
from config.media_cleanup import delete_replaced_file

from .models import BusinessProfile
from .serializers import (
    BusinessRegisterSerializer,
    BusinessProfileSerializer,
)


# ============================================================
# BUSINESS DASHBOARD
# ============================================================

class BusinessDashboardView(APIView):
    permission_classes = [IsBusinessUser]

    def get(self, request):
        try:
            business = BusinessProfile.objects.get(
                user=request.user
            )

            campaigns = CampaignRequest.objects.filter(
                business=business
            )

            total = campaigns.count()

            pending = campaigns.filter(
                status="Pending"
            ).count()

            accepted = campaigns.filter(
                status="Accepted"
            ).count()

            rejected = campaigns.filter(
                status="Rejected"
            ).count()

            completed = campaigns.filter(
                status="Completed"
            ).count()

            cancelled = campaigns.filter(
                status="Cancelled"
            ).count()

            data = {
                "total_campaigns": total,
                "pending": pending,
                "accepted": accepted,
                "rejected": rejected,
                "completed": completed,
                "cancelled": cancelled,
            }

            return Response(
                data,
                status=status.HTTP_200_OK
            )

        except BusinessProfile.DoesNotExist:
            return Response(
                {
                    "error": "Business profile not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )


# ============================================================
# BUSINESS REGISTRATION
# ============================================================

class BusinessRegisterView(APIView):

    # IMPORTANT:
    # Registration must be accessible without login.
    permission_classes = [AllowAny]

    def post(self, request):

        serializer = BusinessRegisterSerializer(
            data=request.data
        )

        if serializer.is_valid():

            serializer.save()

            # Report the real email-delivery result instead of assuming SES
            # accepted the message.
            email_sent = serializer.context.get("email_sent", True)
            message = (
                "Business registered successfully! Verification code sent to your email."
                if email_sent
                else (
                    "Business registered successfully, but the verification email "
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

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


# ============================================================
# BUSINESS PROFILE
# ============================================================

class BusinessProfileView(APIView):
    permission_classes = [IsBusinessUser]
    # Multipart parsers let the logo be uploaded alongside profile fields.
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    # --------------------------------------------------------
    # GET LOGGED-IN BUSINESS PROFILE
    # --------------------------------------------------------

    def get(self, request):

        try:

            business = BusinessProfile.objects.get(
                user=request.user
            )

            serializer = BusinessProfileSerializer(
                business
            )

            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )

        except BusinessProfile.DoesNotExist:

            return Response(
                {
                    "error": "Business profile not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

    # --------------------------------------------------------
    # UPDATE LOGGED-IN BUSINESS PROFILE
    # --------------------------------------------------------

    def put(self, request):
        return self._update(request)

    def patch(self, request):
        return self._update(request)

    def _update(self, request):
        try:
            business = BusinessProfile.objects.get(user=request.user)

            previous_logo_name = business.logo.name if business.logo else ""

            serializer = BusinessProfileSerializer(
                business,
                data=request.data,
                partial=True,
            )

            if serializer.is_valid():
                serializer.save()

                delete_replaced_file(
                    old_name=previous_logo_name,
                    new_name=business.logo.name if business.logo else "",
                )

                data = {**serializer.data, "message": "Business profile updated successfully.", "data": serializer.data}
                return Response(data, status=status.HTTP_200_OK)

            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        except BusinessProfile.DoesNotExist:
            return Response(
                {"error": "Business profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )