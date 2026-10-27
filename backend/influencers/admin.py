from django.contrib import admin

from notifications.services import notify

from .models import InfluencerProfile


@admin.register(InfluencerProfile)
class InfluencerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "category",
        "followers",
        "city",
        "state",
        "email_verified",
        "verification_status",
        "is_verified",
    )
    list_filter = ("verification_status", "is_verified", "email_verified", "category")
    search_fields = ("full_name", "user__username", "user__email", "city", "state")
    readonly_fields = ("social_verification_code",)
    actions = ["approve_verification", "reject_verification"]

    fieldsets = (
        (None, {
            "fields": (
                "user",
                "full_name",
                "bio",
                "category",
                "language",
                "followers",
            )
        }),
        ("Social profiles", {
            "fields": ("instagram", "youtube", "facebook")
        }),
        ("Location", {
            "fields": ("city", "state")
        }),
        ("Media", {
            "fields": ("profile_image",)
        }),
        ("Verification", {
            "fields": (
                "email_verified",
                "verification_status",
                "is_verified",
                "social_verification_code",
            )
        }),
    )

    @admin.action(description="Approve social verification (grant Verified badge)")
    def approve_verification(self, request, queryset):
        for profile in queryset:
            profile.is_verified = True
            profile.verification_status = "Approved"
            profile.save(update_fields=["is_verified", "verification_status"])
            notify(
                recipient=profile.user,
                notification_type="verification",
                title="Profile verified",
                message="Your Instagram ownership was confirmed. Your Verified badge is now live.",
                link="/influencer/profile",
            )
        self.message_user(request, f"{queryset.count()} creator(s) approved.")

    @admin.action(description="Reject social verification")
    def reject_verification(self, request, queryset):
        for profile in queryset:
            profile.is_verified = False
            profile.verification_status = "Rejected"
            profile.social_verification_code = ""
            profile.save(update_fields=["is_verified", "verification_status", "social_verification_code"])
            notify(
                recipient=profile.user,
                notification_type="verification",
                title="Verification rejected",
                message="We could not confirm your Instagram ownership. You can submit the code again after updating your bio.",
                link="/influencer/profile",
            )
        self.message_user(request, f"{queryset.count()} creator(s) rejected.")