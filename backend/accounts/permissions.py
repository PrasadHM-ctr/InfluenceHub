from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import BasePermission

from businesses.models import BusinessProfile
from influencers.models import InfluencerProfile


class IsBusinessUser(BasePermission):
    """Allow access only to an authenticated account with a business profile or platform management access."""

    message = "Only business accounts can perform this action."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            raise NotAuthenticated("Authentication credentials were not provided.")

        if request.user.is_staff or request.user.is_superuser:
            return True
        role = getattr(getattr(request.user, "userrole", None), "role", "").lower()
        if role in ("business", "owner"):
            return True
        return BusinessProfile.objects.filter(user=request.user).exists()


class IsInfluencerUser(BasePermission):
    """Allow access only to an authenticated account with an influencer profile or platform management access."""

    message = "Only influencer accounts can perform this action."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            raise NotAuthenticated("Authentication credentials were not provided.")

        if request.user.is_staff or request.user.is_superuser:
            return True
        role = getattr(getattr(request.user, "userrole", None), "role", "").lower()
        if role in ("influencer", "owner"):
            return True
        return InfluencerProfile.objects.filter(user=request.user).exists()
