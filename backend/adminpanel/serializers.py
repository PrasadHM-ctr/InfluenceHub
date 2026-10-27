"""Input validation for admin panel mutations."""

from rest_framework import serializers

ALLOWED_USER_ACTIONS = ("suspend", "activate", "verify_profile", "reject_profile")


class UserActionSerializer(serializers.Serializer):
    """Validates moderation actions performed on a user account."""

    action = serializers.ChoiceField(choices=ALLOWED_USER_ACTIONS)


class VerificationReviewSerializer(serializers.Serializer):
    """Validates an influencer verification decision."""

    decision = serializers.ChoiceField(choices=("approved", "rejected"))
    reason = serializers.CharField(required=False, allow_blank=True)


class CampaignModerationSerializer(serializers.Serializer):
    """Admin campaign moderation.

    The only permitted change is an explicit force-cancel, and it must
    arrive with ``confirm: true`` so no click can silently alter data.
    """

    status = serializers.ChoiceField(choices=("Cancelled",))
    confirm = serializers.BooleanField()

    def validate_confirm(self, value):
        if value is not True:
            raise serializers.ValidationError("Confirmation is required to modify a campaign.")
        return value
