from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from apps.privacy.consent import SignupConsentFields, pop_signup_consent, record_signup_consent

from .models import User, Address, BuyerProfile, FarmerProfile, DriverProfile, UserRole


class RegisterSerializer(SignupConsentFields, serializers.ModelSerializer):
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all(), message="A user with this email already exists.")]
    )
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    farm_name = serializers.CharField(write_only=True, required=False, allow_blank=False, max_length=255)
    farm_location = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=255, default="")

    class Meta:
        model = User
        fields = [
            "email", "first_name", "last_name", "phone", "role",
            "password", "password_confirm", "farm_name", "farm_location",
            "accept_privacy_policy", "marketing_opt_in",
        ]

    def validate_role(self, value):
        # Admins are created by other admins (createsuperuser / Django admin), never self-registered.
        if value == UserRole.ADMIN:
            raise serializers.ValidationError("Choose customer, farmer or driver.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        if attrs.get("role") == "farmer" and not attrs.get("farm_name", "").strip():
            raise serializers.ValidationError({"farm_name": "Farm name is required when registering as a farmer."})
        return attrs

    def create(self, validated_data):
        farm_name = validated_data.pop("farm_name", "")
        farm_location = validated_data.pop("farm_location", "")
        marketing_opt_in = pop_signup_consent(validated_data)
        user = User.objects.create_user(**validated_data)
        record_signup_consent(user, marketing_opt_in)
        if user.role == "farmer":
            FarmerProfile.objects.create(user=user, farm_name=farm_name, farm_location=farm_location)
        elif user.role == "customer":
            BuyerProfile.objects.create(user=user)
        elif user.role == "driver":
            DriverProfile.objects.create(user=user)
        return user


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    # Admin accounts only: the super admin, as opposed to a manager
    is_super_admin = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name",
            "phone", "role", "status", "date_joined", "is_super_admin",
        ]
        read_only_fields = ["id", "email", "role", "status", "date_joined", "is_super_admin"]

    def get_is_super_admin(self, obj):
        return obj.role == "admin" and obj.is_superuser


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "id", "label", "street_address", "suburb", "city",
            "province", "postal_code", "country", "is_default",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class BuyerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BuyerProfile
        fields = ["buyer_type", "preferred_delivery_address"]
        read_only_fields = ["buyer_type"]


class FarmerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmerProfile
        fields = [
            "id", "farm_name", "farm_description", "farm_location",
            "is_approved", "approved_at", "rejection_reason",
        ]
        read_only_fields = ["id", "is_approved", "approved_at", "rejection_reason"]


class DriverProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverProfile
        fields = [
            "vehicle_type", "vehicle_registration",
            "is_approved", "approved_at", "is_available",
        ]
        read_only_fields = ["is_approved", "approved_at"]


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_str
        from django.utils.http import urlsafe_base64_decode

        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(attrs["uid"])), is_active=True)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            user = None
        if user is None or not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError("This reset link is invalid or has expired. Please request a new one.")

        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        validate_password(attrs["password"], user)

        attrs["user"] = user
        return attrs
