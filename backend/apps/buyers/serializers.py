from decimal import Decimal

from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from apps.privacy.consent import SignupConsentFields, pop_signup_consent, record_signup_consent
from apps.users.models import User

from .models import (
    BusinessApprovalStatus,
    BusinessBuyerDetails,
    BusinessType,
    BuyerAccountMember,
    BuyerAccountMemberRole,
    CreditTerms,
)


class BusinessBuyerSignupSerializer(SignupConsentFields, serializers.Serializer):
    """
    Creates a User (role=customer) + Address + BuyerProfile (buyer_type=business)
    + BusinessBuyerDetails (approval_status=pending) in one call. The signing-up
    user becomes the account's 'owner' BuyerAccountMember.
    """
    # User fields
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all(), message="A user with this email already exists.")]
    )
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")

    # Business fields
    business_name = serializers.CharField(max_length=255)
    business_type = serializers.ChoiceField(choices=BusinessType.choices)
    registration_number = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    credit_terms = serializers.ChoiceField(choices=CreditTerms.choices, default=CreditTerms.PREPAID)
    credit_limit = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)

    # Billing/delivery address — used for both at signup
    street_address = serializers.CharField(max_length=255)
    suburb = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    city = serializers.CharField(max_length=100)
    province = serializers.CharField(max_length=100)
    postal_code = serializers.CharField(max_length=10)

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        from apps.users.models import Address, BuyerProfile, BuyerType

        address_data = {
            key: validated_data.pop(key)
            for key in ["street_address", "suburb", "city", "province", "postal_code"]
        }
        business_data = {
            "business_name": validated_data.pop("business_name"),
            "business_type": validated_data.pop("business_type"),
            "registration_number": validated_data.pop("registration_number", None),
            "credit_terms": validated_data.pop("credit_terms"),
            "credit_limit": validated_data.pop("credit_limit", None),
        }

        marketing_opt_in = pop_signup_consent(validated_data)
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            phone=validated_data.get("phone", ""),
            role="customer",
        )
        record_signup_consent(user, marketing_opt_in)
        address = Address.objects.create(user=user, is_default=True, **address_data)
        buyer_profile = BuyerProfile.objects.create(
            user=user, buyer_type=BuyerType.BUSINESS, preferred_delivery_address=address,
        )
        business_details = BusinessBuyerDetails.objects.create(
            buyer=buyer_profile,
            billing_address=address,
            approval_status=BusinessApprovalStatus.PENDING,
            **business_data,
        )
        BuyerAccountMember.objects.create(
            buyer_profile=buyer_profile, user=user, role=BuyerAccountMemberRole.OWNER,
        )

        return business_details


class BusinessBuyerDetailsSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="buyer.user.email", read_only=True)
    full_name = serializers.CharField(source="buyer.user.full_name", read_only=True)

    class Meta:
        model = BusinessBuyerDetails
        fields = [
            "id", "email", "full_name", "business_name", "business_type",
            "registration_number", "billing_address", "credit_terms", "credit_limit", "commission_rate",
            "approval_status", "rejection_reason", "approved_at", "created_at",
        ]
        read_only_fields = fields


class BusinessApprovalActionSerializer(serializers.Serializer):
    """Input for approve/suspend actions. Mirrors ApprovalActionSerializer in
    apps.users.admin_serializers (farmer/driver review) — a reason is required
    when suspending so BusinessBuyerDetails.rejection_reason is never blank
    for a rejected application."""
    action = serializers.ChoiceField(choices=["approve", "suspend"])
    reason = serializers.CharField(required=False, allow_blank=True)
    # Optional on approval: an agreed commission for this account (5-8%)
    commission_rate = serializers.DecimalField(
        max_digits=4, decimal_places=2, required=False, allow_null=True,
        min_value=Decimal("5.00"), max_value=Decimal("8.00"),
    )

    def validate(self, attrs):
        if attrs["action"] == "suspend" and not attrs.get("reason", "").strip():
            raise serializers.ValidationError({"reason": "A reason is required when suspending."})
        return attrs


class BuyerAccountMemberSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = BuyerAccountMember
        fields = ["id", "user", "email", "full_name", "role", "created_at"]
        read_only_fields = ["id", "user", "email", "full_name", "created_at"]


class BuyerAccountMemberAddSerializer(serializers.Serializer):
    """Input for adding a member — looked up by email since the owner won't know a user's numeric ID."""
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=BuyerAccountMemberRole.choices, default=BuyerAccountMemberRole.BUYER)

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("No user found with this email.")
        self._user = user
        return value

    def validate_role(self, value):
        if value == BuyerAccountMemberRole.OWNER:
            raise serializers.ValidationError("Cannot add a member as owner — ownership is set at signup.")
        return value
