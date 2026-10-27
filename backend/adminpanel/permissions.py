"""Authorization for the owner admin panel.

The decision is made ONLY from server-side database state:
an explicit ``owner`` UserRole row, or the Django superuser flag.
Frontend roles, localStorage values, query parameters and URL
parameters are never consulted for authorization.
"""

from django.core.exceptions import ObjectDoesNotExist
from rest_framework.permissions import BasePermission


def get_stored_role(user) -> str:
    """Return the database role for a user ('' when none exists)."""
    try:
        return user.userrole.role  # type: ignore[union-attr]
    except (AttributeError, ObjectDoesNotExist):
        return ""


def is_owner_admin(user) -> bool:
    """Single source of truth for owner/admin authorization."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if not user.is_active:
        return False
    if getattr(user, "is_superuser", False):
        return True
    return get_stored_role(user) == "owner"


class IsOwnerAdmin(BasePermission):
    """Allow access only to the platform owner/admin account."""

    message = "You do not have permission to access the owner panel."

    def has_permission(self, request, view):
        return is_owner_admin(request.user)
