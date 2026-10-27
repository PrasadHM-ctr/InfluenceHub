"""Owner-only admin API views.

Every view enforces ``IsAuthenticated`` + ``IsOwnerAdmin``; authorization
is resolved exclusively from database state (see permissions.py). List
endpoints use server-side pagination and efficient aggregate queries -
no unbounded result sets ever reach the browser.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.db.models import Count, F, OuterRef, Q, Subquery, Sum
from django.db.models.functions import TruncDate
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts import cognito
from accounts.models import CognitoIdentity, UserRole
from businesses.models import BusinessProfile
from businesses.serializers import business_completion
from campaigns.models import CampaignRequest
from influencers.models import InfluencerProfile
from influencers.serializers import influencer_completion
from notifications.services import notify
from influencers.models import VerificationAudit

from .models import AdminAlertState, AuditLog
from .permissions import IsOwnerAdmin, get_stored_role
from .serializers import (
    CampaignModerationSerializer,
    UserActionSerializer,
    VerificationReviewSerializer,
)
from .services import record_audit


class AdminPagePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def _abs_url(request, file_field) -> str | None:
    """Absolute URL for a stored image (local media or S3)."""
    if not file_field:
        return None
    try:
        return request.build_absolute_uri(file_field.url)
    except (ValueError, AttributeError):
        return None


def _campaign_status_counts() -> dict[str, int]:
    rows = CampaignRequest.objects.values("status").annotate(total=Count("id"))
    return {row["status"]: row["total"] for row in rows}


def _role_counts() -> dict[str, int]:
    return {
        row["role"]: row["total"]
        for row in UserRole.objects.values("role").annotate(total=Count("id"))
    }


def _campaign_activity_subquery(related_profile_attr: str) -> Subquery:
    """Latest campaign update timestamp for the profile related to a user."""
    lookup = (
        {"business": OuterRef(f"{related_profile_attr}__pk")}
        if related_profile_attr == "businessprofile"
        else {"influencer": OuterRef(f"{related_profile_attr}__pk")}
    )
    return Subquery(
        CampaignRequest.objects.filter(**lookup).order_by("-updated_at").values("updated_at")[:1]
    )


def _serialize_user_row(user: User) -> dict:
    role = get_stored_role(user)
    row = {
        "id": user.id,
        "username": user.username,
        "name": user.get_full_name() or user.username,
        "email": user.email,
        "role": role or None,
        "is_superuser": user.is_superuser,
        # Locally, is_active flips to True exactly when the Cognito email
        # confirmation code is accepted - so it doubles as the honest
        # "email verified" signal for every role.
        "email_verified": user.is_active,
        "account_status": "Active" if user.is_active else "Inactive",
        "date_joined": user.date_joined.isoformat(),
        "biz_activity": getattr(user, "biz_activity", None),
        "inf_activity": getattr(user, "inf_activity", None),
        "completion_percentage": None,
        "verification_status": None,
    }
    if hasattr(user, "influencerprofile"):
        completion, _ = influencer_completion(user.influencerprofile)
        row["completion_percentage"] = completion
        row["verification_status"] = user.influencerprofile.verification_status
    elif hasattr(user, "businessprofile"):
        completion_b, _ = business_completion(user.businessprofile)
        row["completion_percentage"] = completion_b
    return row


def _attach_last_activity(rows: list[dict]) -> None:
    """Compute ``last_activity`` per row from prefetched campaign stamps."""
    for row in rows:
        candidates = [
            value
            for value in (row.pop("biz_activity", None), row.pop("inf_activity", None))
            if value
        ]
        row["last_activity"] = max(candidates).isoformat() if candidates else None


class AdminDashboardView(APIView):
    """Aggregated platform statistics - all values computed from PostgreSQL."""

    permission_classes = [IsAuthenticated, IsOwnerAdmin]

    def get(self, request):
        now = timezone.now()
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = day_start - timedelta(days=7)

        role_counts = _role_counts()
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()

        statuses = _campaign_status_counts()
        budget = CampaignRequest.objects.aggregate(total=Sum("budget"))["total"] or 0

        return Response(
            {
                "users": {
                    "total": total_users,
                    "business": role_counts.get("business", 0),
                    "influencer": role_counts.get("influencer", 0),
                    "owner": role_counts.get("owner", 0),
                    # Email-confirmed accounts (Cognito OTP completed) vs pending.
                    "verified": active_users,
                    "unverified": total_users - active_users,
                    "new_today": User.objects.filter(date_joined__gte=day_start).count(),
                    "new_this_week": User.objects.filter(date_joined__gte=week_ago).count(),
                },
                "campaigns": {
                    "total": sum(statuses.values()),
                    "pending": statuses.get("Pending", 0),
                    "accepted": statuses.get("Accepted", 0),
                    "rejected": statuses.get("Rejected", 0),
                    "completed": statuses.get("Completed", 0),
                    "cancelled": statuses.get("Cancelled", 0),
                    "new_today": CampaignRequest.objects.filter(created_at__gte=day_start).count(),
                    # Safely aggregated total; per-campaign budgets stay in their views.
                    "budget_total": str(budget),
                },
                "moderation": {
                    # Influencer badge verifications still under review.
                    "pending_verifications": InfluencerProfile.objects.filter(
                        verification_status="Pending"
                    ).count(),
                    "approved_verifications": InfluencerProfile.objects.filter(
                        verification_status="Approved"
                    ).count(),
                    "rejected_verifications": InfluencerProfile.objects.filter(
                        verification_status="Rejected"
                    ).count(),
                    "inactive_accounts": total_users - active_users,
                },
            }
        )


class AdminUserListView(APIView):
    """Server-side paginated / searchable / filterable user directory."""

    permission_classes = [IsAuthenticated, IsOwnerAdmin]

    SORTS = {
        "newest": "-date_joined",
        "oldest": "date_joined",
        "name": "username",
        "email": "email",
    }

    def get(self, request):
        users = User.objects.select_related("userrole").annotate(
            biz_activity=_campaign_activity_subquery("businessprofile"),
            inf_activity=_campaign_activity_subquery("influencerprofile"),
        )

        search = (request.query_params.get("search") or "").strip()
        if search:
            users = users.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(influencerprofile__full_name__icontains=search)
                | Q(businessprofile__company_name__icontains=search)
            ).distinct()

        role_filter = request.query_params.get("role") or ""
        if role_filter == "none":
            users = users.filter(userrole__isnull=True)
        elif role_filter:
            users = users.filter(userrole__role=role_filter)

        verification = request.query_params.get("verification") or ""
        if verification in ("verified", "unverified"):
            users = users.filter(is_active=(verification == "verified"))

        status_filter = request.query_params.get("status") or ""
        if status_filter in ("active", "inactive"):
            users = users.filter(is_active=(status_filter == "active"))

        order_by = self.SORTS.get(request.query_params.get("sort") or "", "-date_joined")
        users = users.order_by(order_by)

        paginator = AdminPagePagination()
        page_rows = paginator.paginate_queryset(users, request, view=self)
        rows = [_serialize_user_row(row) for row in page_rows]
        _attach_last_activity(rows)
        response = paginator.get_paginated_response(rows)
        response.data["role_counts"] = _role_counts()
        return response


class AdminUserDetailView(APIView):
    """Full moderation detail plus guarded actions for one account."""

    permission_classes = [IsAuthenticated, IsOwnerAdmin]

    def get(self, request, pk: int):
        user = User.objects.filter(pk=pk).first()
        if not user:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        record_audit(
            actor=request.user,
            action="user_viewed",
            target_type="user",
            target_id=user.pk,
            description=f"Viewed user {user.username}",
        )
        return Response(_serialize_user_detail(request, user))

    def patch(self, request, pk: int):
        user = User.objects.filter(pk=pk).first()
        if not user:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data["action"]

        if action == "suspend" and user.pk == request.user.pk:
            return Response(
                {"detail": "You cannot suspend your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if action == "suspend":
            if not user.is_active:
                return Response(
                    {"detail": "Account is already inactive."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.is_active = False
            user.save(update_fields=["is_active"])
            record_audit(actor=request.user, action="user_suspended", target_type="user",
                         target_id=user.pk, description=f"Suspended {user.username}")
            notify(recipient=user, notification_type="verification", title="Account suspended",
                   message="Your InfluenceHub account has been suspended by an administrator.")
            return Response({"detail": f"{user.username} suspended.", "account_status": "Inactive"})

        if action == "activate":
            if user.is_active:
                return Response(
                    {"detail": "Account is already active."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.is_active = True
            user.save(update_fields=["is_active"])
            record_audit(actor=request.user, action="user_activated", target_type="user",
                         target_id=user.pk, description=f"Activated {user.username}")
            notify(recipient=user, notification_type="verification", title="Account reactivated",
                   message="Your InfluenceHub account has been reactivated.")
            return Response({"detail": f"{user.username} activated.", "account_status": "Active"})

        # Verification decisions apply only to influencer accounts.
        if not hasattr(user, "influencerprofile"):
            return Response(
                {"detail": "Verification actions apply to influencer accounts only."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        profile: InfluencerProfile = user.influencerprofile
        if action == "verify_profile":
            profile.verification_status = "Approved"
            profile.is_verified = True
            profile.reviewed_by = request.user
            profile.verification_reviewed_at = timezone.now()
            profile.verification_rejection_reason = ""
            profile.save(update_fields=["verification_status", "is_verified", "reviewed_by", "verification_reviewed_at", "verification_rejection_reason"])
            VerificationAudit.objects.create(
                profile=profile,
                action=VerificationAudit.ACTION_APPROVED,
                reviewed_by=request.user,
            )
            record_audit(actor=request.user, action="user_approved", target_type="user",
                         target_id=user.pk, description=f"Approved verification for {user.username}")
            notify(recipient=user, notification_type="verification", title="Profile approved",
                   message="Your creator profile has been reviewed and approved.",
                   link="/influencer/profile")
            return Response({"detail": f"{user.username} approved.", "verification_status": "Approved"})

        profile.verification_status = "Rejected"
        profile.is_verified = False
        profile.reviewed_by = request.user
        profile.verification_reviewed_at = timezone.now()
        profile.save(update_fields=["verification_status", "is_verified", "reviewed_by", "verification_reviewed_at"])
        VerificationAudit.objects.create(
            profile=profile,
            action=VerificationAudit.ACTION_REJECTED,
            reviewed_by=request.user,
        )
        record_audit(actor=request.user, action="user_rejected", target_type="user",
                     target_id=user.pk, description=f"Rejected verification for {user.username}")
        notify(recipient=user, notification_type="verification", title="Profile rejected",
               message="Your creator profile was reviewed and could not be approved.",
               link="/influencer/profile")
        return Response({"detail": f"{user.username} rejected.", "verification_status": "Rejected"})

    def delete(self, request, pk: int):
        user = User.objects.filter(pk=pk).first()
        if not user:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        if user.pk == request.user.pk:
            return Response(
                {"detail": "You cannot delete your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Remove the authentication identity FIRST, resolved from OUR database
        # (immutable sub recorded at login; email fallback) - never from any
        # client-supplied identifier. Skipping this leaves a live Cognito
        # account behind whose email can never be registered again.
        username = user.username
        identity = CognitoIdentity.objects.filter(user=user).first()
        try:
            cognito.delete_user(sub=identity.sub if identity else "", email=user.email)
        except cognito.CognitoError as error:
            # Never create an inconsistent state: if the auth record survives,
            # application data stays untouched so the admin can simply retry.
            hint = (
                " The app AWS role lacks cognito-idp:AdminDeleteUser - "
                "apply the updated iam.tf and retry. No data was deleted."
                if error.aws_code == "AccessDeniedException"
                else " No data was deleted - please try again."
            )
            return Response(
                {"detail": f"Could not delete the authentication record for {username}. {hint}".strip()},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Audit before the row disappears - the actor reference survives via SET_NULL.
        record_audit(
            actor=request.user,
            action="user_deleted",
            target_type="user",
            target_id=pk,
            description=f"Permanently deleted {username}",
        )
        with transaction.atomic():
            user.delete()  # Related profiles/data follow the existing FK policy.
        return Response(status=status.HTTP_204_NO_CONTENT)


def _risk_signals(profile: InfluencerProfile, completion: int, campaign_count: int) -> dict:
    """Transparent heuristic signals for moderators.

    A review-priority indicator ONLY - never proof of fraud and never
    derived from follower count alone.
    """
    score = 0
    signals: list[str] = []
    if not profile.email_verified:
        score += 30
        signals.append("Email address has not been verified")
    if completion < 50:
        score += 20
        signals.append(f"Profile only {completion}% complete")
    if not any([profile.instagram, profile.youtube, profile.facebook]):
        score += 15
        signals.append("No social links provided")
    if campaign_count == 0:
        score += 10
        signals.append("No campaign history yet")
    if profile.verification_status != "Approved":
        score += 5
        signals.append("Profile is not badge-verified yet")
    return {"score": min(score, 100), "signals": signals}


def _serialize_user_detail(request, user: User) -> dict:
    role = get_stored_role(user)
    campaigns_filter = Q(business__user=user) | Q(influencer__user=user)
    campaign_totals = dict(
        CampaignRequest.objects.filter(campaigns_filter)
        .values_list("status")
        .annotate(total=Count("id"))
    )
    recent_campaigns = (
        CampaignRequest.objects.filter(campaigns_filter)
        .select_related("business", "influencer")
        .order_by("-updated_at")[:8]
    )

    last_activity = None
    for lookup in ("business__user", "influencer__user"):
        stamp = (
            CampaignRequest.objects.filter(**{lookup: user})
            .order_by("-updated_at")
            .values_list("updated_at", flat=True)[:1]
        )
        if stamp:
            last_activity = stamp[0] if last_activity is None else max(last_activity, stamp[0])

    detail: dict = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": role or None,
        "is_superuser": user.is_superuser,
        "email_verified": user.is_active,
        "account_status": "Active" if user.is_active else "Inactive",
        "date_joined": user.date_joined.isoformat(),
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "last_activity": last_activity.isoformat() if last_activity else None,
        "profile": None,
        "campaigns": {
            "total": sum(campaign_totals.values()),
            "by_status": campaign_totals,
            "recent": [
                {
                    "id": item.id,
                    "title": item.title,
                    "status": item.status,
                    "budget": str(item.budget),
                    "business": item.business.company_name,
                    "influencer": item.influencer.full_name,
                    "created_at": item.created_at.isoformat(),
                    "updated_at": item.updated_at.isoformat(),
                }
                for item in recent_campaigns
            ],
        },
    }

    if hasattr(user, "influencerprofile"):
        p: InfluencerProfile = user.influencerprofile
        completion_pct, missing = influencer_completion(p)
        risk = _risk_signals(p, completion_pct, sum(campaign_totals.values()))
        detail["profile"] = {
            "type": "influencer",
            "full_name": p.full_name,
            "bio": p.bio,
            "category": p.category,
            "language": p.language,
            "followers": p.followers,
            "city": p.city,
            "state": p.state,
            "instagram": p.instagram or "",
            "youtube": p.youtube or "",
            "facebook": p.facebook or "",
            "email_verified": p.email_verified,
            "is_verified": p.is_verified,
            "verification_status": p.verification_status,
            "social_code_configured": bool(p.social_verification_code),
            "social_verification_code": p.social_verification_code or "",
            "verification_code": p.social_verification_code or "",
            "verification_submitted_at": p.verification_submitted_at.isoformat() if p.verification_submitted_at else None,
            "verification_reviewed_at": p.verification_reviewed_at.isoformat() if p.verification_reviewed_at else None,
            "verification_rejection_reason": p.verification_rejection_reason or "",
            "image_url": _abs_url(request, p.profile_image),
            "completion_percentage": completion_pct,
            "missing_fields": missing,
            "risk_score": risk["score"],
            "risk_signals": risk["signals"],
        }
    elif hasattr(user, "businessprofile"):
        b: BusinessProfile = user.businessprofile
        completion_pct, missing = business_completion(b)
        detail["profile"] = {
            "type": "business",
            "company_name": b.company_name,
            "industry": b.industry,
            "website": b.website or "",
            "description": b.description,
            "phone": b.phone,
            "city": b.city,
            "state": b.state,
            "logo_url": _abs_url(request, b.logo),
            "completion_percentage": completion_pct,
            "missing_fields": missing,
        }
    return detail


class AdminInfluencerListView(APIView):
    """Influencer directory with fraud-prevention review signals."""

    permission_classes = [IsAuthenticated, IsOwnerAdmin]

    def get(self, request):
        profiles = InfluencerProfile.objects.select_related("user").annotate(
            campaign_count=Count("campaigns_received", distinct=True),
            completed_count=Count(
                "campaigns_received",
                filter=Q(campaigns_received__status="Completed"),
                distinct=True,
            ),
        )

        search = (request.query_params.get("search") or "").strip()
        if search:
            profiles = profiles.filter(
                Q(full_name__icontains=search) | Q(user__email__icontains=search)
            ).distinct()

        verification = request.query_params.get("verification") or ""
        if verification in ("Pending", "Approved", "Rejected"):
            profiles = profiles.filter(verification_status=verification)

        status_filter = request.query_params.get("status") or ""
        if status_filter in ("active", "inactive"):
            profiles = profiles.filter(user__is_active=(status_filter == "active"))

        paginator = AdminPagePagination()
        page_rows = paginator.paginate_queryset(profiles.order_by("-user__date_joined"), request, view=self)
        rows = []
        for p in page_rows:
            completion_pct, _ = influencer_completion(p)
            risk = _risk_signals(p, completion_pct, p.campaign_count)
            rows.append(
                {
                    "id": p.pk,
                    "user_id": p.user_id,
                    "full_name": p.full_name,
                    "email": p.user.email,
                    "category": p.category,
                    "language": p.language,
                    "city": p.city,
                    "state": p.state,
                    "followers": p.followers,
                    "email_verified": p.email_verified,
                    "account_status": "Active" if p.user.is_active else "Inactive",
                    "verification_status": p.verification_status,
                    "social_verification_code": p.social_verification_code or "",
                    "social_code_configured": bool(p.social_verification_code),
                    "campaign_count": p.campaign_count,
                    "completed_campaigns": p.completed_count,
                    "completion_percentage": completion_pct,
                    "risk_score": risk["score"],
                    "risk_signals": risk["signals"],
                    "image_url": _abs_url(request, p.profile_image),
                    "created_at": p.user.date_joined.isoformat(),
                }
            )
        return paginator.get_paginated_response(rows)


class AdminBusinessListView(APIView):
    """Business directory for owner oversight."""

    permission_classes = [IsAuthenticated, IsOwnerAdmin]

    def get(self, request):
        profiles = BusinessProfile.objects.select_related("user").annotate(
            campaign_count=Count("campaigns_sent", distinct=True),
            completed_count=Count(
                "campaigns_sent",
                filter=Q(campaigns_sent__status="Completed"),
                distinct=True,
            ),
        )

        search = (request.query_params.get("search") or "").strip()
        if search:
            profiles = profiles.filter(
                Q(company_name__icontains=search) | Q(user__email__icontains=search)
            ).distinct()

        status_filter = request.query_params.get("status") or ""
        if status_filter in ("active", "inactive"):
            profiles = profiles.filter(user__is_active=(status_filter == "active"))

        paginator = AdminPagePagination()
        page_rows = paginator.paginate_queryset(profiles.order_by("-user__date_joined"), request, view=self)
        rows = []
        for b in page_rows:
            completion_pct, _ = business_completion(b)
            rows.append(
                {
                    "id": b.pk,
                    "user_id": b.user_id,
                    "company_name": b.company_name,
                    "email": b.user.email,
                    "industry": b.industry,
                    "city": b.city,
                    "state": b.state,
                    "website": b.website or "",
                    "email_verified": b.user.is_active,
                    "account_status": "Active" if b.user.is_active else "Inactive",
                    "campaign_count": b.campaign_count,
                    "completed_campaigns": b.completed_count,
                    "completion_percentage": completion_pct,
                    "logo_url": _abs_url(request, b.logo),
                    "created_at": b.user.date_joined.isoformat(),
                }
            )
        return paginator.get_paginated_response(rows)


class AdminCampaignListView(APIView):
    """Campaign oversight with status filters and participant search."""

    permission_classes = [IsAuthenticated, IsOwnerAdmin]

    def get(self, request):
        campaigns = CampaignRequest.objects.select_related(
            "business", "influencer", "business__user", "influencer__user"
        )

        campaign_status = request.query_params.get("status") or ""
        if campaign_status in ("Pending", "Accepted", "Rejected", "Completed", "Cancelled"):
            campaigns = campaigns.filter(status=campaign_status)

        search = (request.query_params.get("search") or "").strip()
        if search:
            campaigns = campaigns.filter(
                Q(title__icontains=search)
                | Q(business__company_name__icontains=search)
                | Q(influencer__full_name__icontains=search)
            ).distinct()

        paginator = AdminPagePagination()
        page_rows = paginator.paginate_queryset(campaigns.order_by("-created_at"), request, view=self)
        rows = [
            {
                "id": c.id,
                "business_id": c.business_id,
                "business": c.business.company_name,
                "influencer_id": c.influencer_id,
                "influencer": c.influencer.full_name,
                "title": c.title,
                "budget": str(c.budget),
                "status": c.status,
                "has_attachment": bool(c.attachment),
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
            }
            for c in page_rows
        ]
        response = paginator.get_paginated_response(rows)
        response.data["status_counts"] = _campaign_status_counts()
        return response


class AdminCampaignDetailView(APIView):
    """Inspect one campaign; moderate only with explicit confirmation."""

    permission_classes = [IsAuthenticated, IsOwnerAdmin]

    def get(self, request, pk: int):
        campaign = (
            CampaignRequest.objects.select_related(
                "business", "influencer", "business__user", "influencer__user"
            )
            .filter(pk=pk)
            .first()
        )
        if not campaign:
            return Response({"detail": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND)

        record_audit(
            actor=request.user,
            action="campaign_viewed",
            target_type="campaign",
            target_id=campaign.pk,
            description=f"Viewed campaign {campaign.title}",
        )
        return Response(
            {
                "id": campaign.id,
                "title": campaign.title,
                "message": campaign.message,
                "budget": str(campaign.budget),
                "status": campaign.status,
                "attachment_url": _abs_url(request, campaign.attachment),
                # Distinct keys so nested objects never collide with the
                # plain-string participant names used by the list endpoint.
                "business_detail": {
                    "id": campaign.business.pk,
                    "company_name": campaign.business.company_name,
                    "email": campaign.business.user.email,
                    "city": campaign.business.city,
                    "state": campaign.business.state,
                },
                "influencer_detail": {
                    "id": campaign.influencer.pk,
                    "full_name": campaign.influencer.full_name,
                    "email": campaign.influencer.user.email,
                    "followers": campaign.influencer.followers,
                    "category": campaign.influencer.category,
                },
                "created_at": campaign.created_at.isoformat(),
                "updated_at": campaign.updated_at.isoformat(),
            }
        )

    def patch(self, request, pk: int):
        campaign = CampaignRequest.objects.filter(pk=pk).first()
        if not campaign:
            return Response({"detail": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = CampaignModerationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if campaign.status == "Cancelled":
            return Response(
                {"detail": "Campaign is already cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        campaign.status = "Cancelled"
        campaign.save(update_fields=["status", "updated_at"])
        record_audit(
            actor=request.user,
            action="campaign_cancelled",
            target_type="campaign",
            target_id=campaign.pk,
            description=f"Force-cancelled campaign {campaign.title}",
        )
        notify(
            recipient=campaign.business.user,
            notification_type="campaign_cancelled",
            title="Campaign cancelled",
            message=f'Your campaign "{campaign.title}" was cancelled by an administrator.',
            link="/business/dashboard",
        )
        notify(
            recipient=campaign.influencer.user,
            notification_type="campaign_cancelled",
            title="Campaign cancelled",
            message=f'The campaign "{campaign.title}" was cancelled by an administrator.',
            link="/influencer/dashboard",
        )
        return Response({"detail": f"Campaign {campaign.pk} cancelled.", "status": "Cancelled"})


class AdminVerificationQueueView(APIView):
    """Influencer badge-verification review queue (reuses the existing
    InfluencerProfile.verification_status concept - no invented states)."""

    permission_classes = [IsAuthenticated, IsOwnerAdmin]

    def get(self, request):
        verification_status = request.query_params.get("status") or "Pending"
        if verification_status not in ("Pending", "Approved", "Rejected", "all"):
            verification_status = "Pending"

        profiles = InfluencerProfile.objects.select_related("user")
        if verification_status != "all":
            profiles = profiles.filter(verification_status=verification_status)

        search = (request.query_params.get("search") or "").strip()
        if search:
            profiles = profiles.filter(
                Q(full_name__icontains=search)
                | Q(user__email__icontains=search)
                | Q(user__username__icontains=search)
                | Q(instagram__icontains=search)
                | Q(social_verification_code__icontains=search)
            ).distinct()

        paginator = AdminPagePagination()
        ordered_profiles = profiles.order_by(
            F("verification_submitted_at").desc(nulls_last=True),
            "-user__date_joined",
        )
        page_rows = paginator.paginate_queryset(ordered_profiles, request, view=self)
        rows = []
        for p in page_rows:
            completion_pct, missing = influencer_completion(p)
            risk = _risk_signals(p, completion_pct, p.campaigns_received.count())
            rows.append(
                {
                    "id": p.pk,
                    "user_id": p.user_id,
                    "username": p.user.username,
                    "full_name": p.full_name,
                    "email": p.user.email,
                    "category": p.category,
                    "language": p.language,
                    "city": p.city,
                    "state": p.state,
                    "followers": p.followers,
                    "bio": p.bio,
                    "instagram": p.instagram or "",
                    "youtube": p.youtube or "",
                    "facebook": p.facebook or "",
                    # Generated verification code to compare against Instagram bio
                    "social_verification_code": p.social_verification_code or "",
                    "verification_code": p.social_verification_code or "",
                    "social_code_configured": bool(p.social_verification_code),
                    "email_verified": p.email_verified,
                    "account_status": "Active" if p.user.is_active else "Inactive",
                    "is_verified": p.is_verified,
                    "verification_status": p.verification_status,
                    "verification_submitted_at": p.verification_submitted_at.isoformat() if p.verification_submitted_at else None,
                    "verification_reviewed_at": p.verification_reviewed_at.isoformat() if p.verification_reviewed_at else None,
                    "verification_rejection_reason": p.verification_rejection_reason or "",
                    "reviewed_by": p.reviewed_by.username if p.reviewed_by else None,
                    "image_url": _abs_url(request, p.profile_image),
                    "completion_percentage": completion_pct,
                    "missing_fields": missing,
                    "risk_score": risk["score"],
                    "risk_signals": risk["signals"],
                    "created_at": p.user.date_joined.isoformat(),
                }
            )
        response = paginator.get_paginated_response(rows)
        counts = {
            row["verification_status"]: row["total"]
            for row in InfluencerProfile.objects.values("verification_status").annotate(total=Count("id"))
        }
        counts["all"] = sum(counts.values())
        response.data["counts"] = counts
        return response


class AdminVerificationReviewView(APIView):
    """Approve or reject an influencer verification request."""

    permission_classes = [IsAuthenticated, IsOwnerAdmin]

    def post(self, request, pk: int):
        profile = InfluencerProfile.objects.select_related("user").filter(pk=pk).first()
        if not profile:
            return Response({"detail": "Verification request not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = VerificationReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = serializer.validated_data["decision"]
        reason = serializer.validated_data.get("reason", "")

        profile.verification_status = "Approved" if decision == "approved" else "Rejected"
        profile.is_verified = decision == "approved"
        profile.reviewed_by = request.user
        profile.verification_reviewed_at = timezone.now()
        if decision == "rejected":
            profile.verification_rejection_reason = reason
        else:
            profile.verification_rejection_reason = ""
        profile.save(update_fields=["verification_status", "is_verified", "reviewed_by", "verification_reviewed_at", "verification_rejection_reason"])

        record_audit(
            actor=request.user,
            action="user_approved" if decision == "approved" else "user_rejected",
            target_type="influencer_profile",
            target_id=profile.pk,
            description=f"Verification {decision} for {profile.full_name}",
        )

        if decision == "rejected":
            VerificationAudit.objects.create(
                profile=profile,
                action=VerificationAudit.ACTION_REJECTED,
                reason=reason,
                reviewed_by=request.user,
            )
            notify(
                recipient=profile.user,
                notification_type="verification",
                title="Profile rejected",
                message=f"Your creator profile was reviewed and could not be approved. Reason: {reason or 'No reason provided.'}",
                link="/influencer/profile",
            )
        else:
            VerificationAudit.objects.create(
                profile=profile,
                action=VerificationAudit.ACTION_APPROVED,
                reviewed_by=request.user,
            )
            notify(
                recipient=profile.user,
                notification_type="verification",
                title="Profile approved",
                message="Your creator profile has been reviewed and approved.",
                link="/influencer/profile",
            )
        return Response(
            {
                "detail": f"{profile.full_name} {decision}.",
                "verification_status": profile.verification_status,
                "is_verified": profile.is_verified,
                "reviewed_by": profile.reviewed_by.username if profile.reviewed_by else None,
                "reviewed_at": profile.verification_reviewed_at.isoformat() if profile.verification_reviewed_at else None,
            }
        )


def _daily_series(queryset, timestamp_field: str, days: int) -> list[dict]:
    """Zero-filled daily counts for the last ``days`` days."""
    start = (timezone.now() - timedelta(days=days - 1)).date()
    truncated = (
        queryset.annotate(bucket=TruncDate(timestamp_field))
        .filter(bucket__gte=start)
        .values("bucket")
        .annotate(total=Count("id"))
    )
    counts = {row["bucket"]: row["total"] for row in truncated}
    series = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        series.append({"date": day.isoformat(), "count": counts.get(day, 0)})
    return series


class AdminAnalyticsView(APIView):
    """Real platform analytics computed with database aggregation."""

    permission_classes = [IsAuthenticated, IsOwnerAdmin]

    def get(self, request):
        role_counts = _role_counts()
        statuses = _campaign_status_counts()

        business_ids = UserRole.objects.filter(role="business").values_list("user_id", flat=True)
        influencer_ids = UserRole.objects.filter(role="influencer").values_list("user_id", flat=True)
        budget_total = CampaignRequest.objects.aggregate(total=Sum("budget"))["total"] or 0

        return Response(
            {
                "totals": {
                    "users": User.objects.count(),
                    "business_users": role_counts.get("business", 0),
                    "influencers": role_counts.get("influencer", 0),
                    "verified_users": User.objects.filter(is_active=True).count(),
                    "unverified_users": User.objects.filter(is_active=False).count(),
                    "campaigns": sum(statuses.values()),
                    "accepted_campaigns": statuses.get("Accepted", 0),
                    "completed_campaigns": statuses.get("Completed", 0),
                    "rejected_campaigns": statuses.get("Rejected", 0),
                    "budget_total": str(budget_total),
                },
                "users_over_time": _daily_series(User.objects, "date_joined", 14),
                "business_registrations": _daily_series(
                    User.objects.filter(id__in=business_ids), "date_joined", 14
                ),
                "influencer_registrations": _daily_series(
                    User.objects.filter(id__in=influencer_ids), "date_joined", 14
                ),
                "campaign_activity": _daily_series(CampaignRequest.objects, "created_at", 14),
                "campaign_status_distribution": [
                    {"status": key, "count": value} for key, value in sorted(statuses.items())
                ],
            }
        )


class AdminActivityLogView(APIView):
    """Paginated audit trail of privileged admin actions."""

    permission_classes = [IsAuthenticated, IsOwnerAdmin]

    def get(self, request):
        entries = AuditLog.objects.select_related("actor")
        action_filter = request.query_params.get("action") or ""
        valid_actions = {choice[0] for choice in AuditLog.ACTION_CHOICES}
        if action_filter in valid_actions:
            entries = entries.filter(action=action_filter)

        paginator = AdminPagePagination()
        page_rows = paginator.paginate_queryset(entries, request, view=self)
        rows = [
            {
                "id": entry.id,
                "actor": entry.actor.username if entry.actor else "(removed account)",
                "action": entry.action,
                "target_type": entry.target_type,
                "target_id": entry.target_id,
                "description": entry.description,
                "created_at": entry.created_at.isoformat(),
            }
            for entry in page_rows
        ]
        return paginator.get_paginated_response(rows)


class AdminNotificationsView(APIView):
    """Attention feed built live from real data; unread state persisted."""

    permission_classes = [IsAuthenticated, IsOwnerAdmin]

    def get(self, request):
        now = timezone.now()
        week_ago = now - timedelta(days=7)
        state = AdminAlertState.objects.first()
        last_read = state.last_read_at if state else None

        pending_verifications = InfluencerProfile.objects.filter(verification_status="Pending")
        raw_items = [
            {
                "key": "pending_verifications",
                "label": "Creator verifications awaiting review",
                "count": pending_verifications.count(),
                "link": "/owner/verifications",
                "latest_at": _first_date(
                    pending_verifications.order_by("-user__date_joined")
                    .values_list("user__date_joined", flat=True)[:1]
                ),
            },
            {
                "key": "new_businesses",
                "label": "New businesses this week",
                "count": User.objects.filter(userrole__role="business", date_joined__gte=week_ago).count(),
                "link": "/owner/businesses",
                "latest_at": _first_date(
                    User.objects.filter(userrole__role="business")
                    .order_by("-date_joined").values_list("date_joined", flat=True)[:1]
                ),
            },
            {
                "key": "new_influencers",
                "label": "New influencers this week",
                "count": User.objects.filter(userrole__role="influencer", date_joined__gte=week_ago).count(),
                "link": "/owner/influencers",
                "latest_at": _first_date(
                    User.objects.filter(userrole__role="influencer")
                    .order_by("-date_joined").values_list("date_joined", flat=True)[:1]
                ),
            },
            {
                "key": "unverified_accounts",
                "label": "Accounts with unconfirmed email",
                "count": User.objects.filter(is_active=False).count(),
                "link": "/owner/users?verification=unverified",
                "latest_at": _first_date(
                    User.objects.filter(is_active=False)
                    .order_by("-date_joined").values_list("date_joined", flat=True)[:1]
                ),
            },
            {
                "key": "cancelled_campaigns",
                "label": "Cancelled campaigns",
                "count": CampaignRequest.objects.filter(status="Cancelled").count(),
                "link": "/owner/campaigns?status=Cancelled",
                "latest_at": _first_date(
                    CampaignRequest.objects.filter(status="Cancelled")
                    .order_by("-updated_at").values_list("updated_at", flat=True)[:1]
                ),
            },
        ]

        unread_count = 0
        results = []
        for item in raw_items:
            latest = item.pop("latest_at")
            is_unread = bool(latest and (last_read is None or latest > last_read))
            item["latest_at"] = latest.isoformat() if latest else None
            item["is_unread"] = is_unread and item["count"] > 0
            if item["is_unread"]:
                unread_count += 1
            results.append(item)

        return Response({"unread_count": unread_count, "results": results})

    def post(self, request):
        """Mark the attention feed as reviewed."""
        state = AdminAlertState.objects.first()
        if state is None:
            AdminAlertState.objects.create(last_read_at=timezone.now())
        else:
            state.last_read_at = timezone.now()
            state.save(update_fields=["last_read_at"])
        record_audit(actor=request.user, action="alerts_seen", target_type="admin_alerts")
        return Response({"detail": "Alerts marked as seen.", "unread_count": 0})


def _first_date(values):
    """``values_list(...)[:1]`` -> first datetime or None."""
    for value in values:
        return value
    return None


class AdminSettingsView(APIView):
    """Read-only owner/security overview for the Settings page."""

    permission_classes = [IsAuthenticated, IsOwnerAdmin]

    def get(self, request):
        owners = User.objects.filter(
            Q(userrole__role="owner") | Q(is_superuser=True), is_active=True
        ).distinct()
        recent_admin_actions = AuditLog.objects.select_related("actor")[:10]
        return Response(
            {
                "session_user": {
                    "id": request.user.id,
                    "username": request.user.username,
                    "email": request.user.email,
                    "role": get_stored_role(request.user) or None,
                    "is_superuser": request.user.is_superuser,
                    "date_joined": request.user.date_joined.isoformat(),
                },
                "owner_accounts": [
                    {
                        "id": o.id,
                        "username": o.username,
                        "email": o.email,
                        "is_superuser": o.is_superuser,
                        "date_joined": o.date_joined.isoformat(),
                    }
                    for o in owners
                ],
                "recent_admin_actions": [
                    {
                        "id": entry.id,
                        "actor": entry.actor.username if entry.actor else "(removed account)",
                        "action": entry.action,
                        "description": entry.description,
                        "created_at": entry.created_at.isoformat(),
                    }
                    for entry in recent_admin_actions
                ],
            }
        )


class AdminLoginAuditView(APIView):
    """Records an admin-login audit entry after a verified owner sign-in."""

    permission_classes = [IsAuthenticated, IsOwnerAdmin]

    def post(self, request):
        record_audit(
            actor=request.user,
            action="admin_login",
            target_type="admin_session",
            target_id=request.user.pk,
            description=f"Owner panel session started for {request.user.username}",
        )
        return Response({"detail": "Login recorded."})
