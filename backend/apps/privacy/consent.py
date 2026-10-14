"""
Consent captured at signup. Every signup path (users.RegisterSerializer,
buyers.BusinessBuyerSignupSerializer) calls record_signup_consent() so a
ConsentRecord exists for data collection before any personal data is used.
"""
from rest_framework import serializers

from .models import ConsentRecord, ConsentType


class SignupConsentFields(serializers.Serializer):
    """Mixin fields for signup serializers. accept_privacy_policy must be true."""
    accept_privacy_policy = serializers.BooleanField(write_only=True)
    marketing_opt_in = serializers.BooleanField(write_only=True, required=False, default=False)

    def validate_accept_privacy_policy(self, value):
        if not value:
            raise serializers.ValidationError("You must accept the privacy policy to create an account.")
        return value


def pop_signup_consent(validated_data):
    """Removes the consent fields from validated_data, returning marketing_opt_in."""
    validated_data.pop("accept_privacy_policy", None)
    return validated_data.pop("marketing_opt_in", False)


def record_signup_consent(user, marketing_opt_in):
    data_collection, _ = ConsentRecord.objects.get_or_create(user=user, consent_type=ConsentType.DATA_COLLECTION)
    data_collection.grant()

    marketing, _ = ConsentRecord.objects.get_or_create(user=user, consent_type=ConsentType.MARKETING)
    if marketing_opt_in:
        marketing.grant()
    else:
        marketing.revoke()
