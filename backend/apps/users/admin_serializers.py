from rest_framework import serializers
from .models import DriverProfile, FarmerProfile, User


class PendingFarmerSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    user_status = serializers.CharField(source="user.status", read_only=True)
    date_joined = serializers.DateTimeField(source="user.date_joined", read_only=True)

    class Meta:
        model = FarmerProfile
        fields = [
            "id", "email", "full_name", "user_status",
            "farm_name", "farm_description", "farm_location",
            "is_approved", "approved_at", "rejection_reason", "date_joined",
        ]


class PendingDriverSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    user_status = serializers.CharField(source="user.status", read_only=True)
    date_joined = serializers.DateTimeField(source="user.date_joined", read_only=True)

    class Meta:
        model = DriverProfile
        fields = [
            "id", "email", "full_name", "user_status",
            "vehicle_type", "vehicle_registration",
            "is_approved", "approved_at", "rejection_reason", "date_joined",
        ]


class ApprovalActionSerializer(serializers.Serializer):
    """Input for approve/reject actions."""
    action = serializers.ChoiceField(choices=["approve", "reject"])
    reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs["action"] == "reject" and not attrs.get("reason", "").strip():
            raise serializers.ValidationError({"reason": "A reason is required when rejecting."})
        return attrs


class AdminUserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "email", "full_name", "first_name", "last_name",
            "phone", "role", "status", "date_joined",
        ]
        read_only_fields = fields


class UserDeactivateSerializer(serializers.Serializer):
    """No input needed — deactivation is the only action on this endpoint."""
    pass
