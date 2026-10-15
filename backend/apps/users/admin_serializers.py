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
    # Annotated by AdminDriverViewSet: buyers' ratings, to help when assigning deliveries
    average_rating = serializers.FloatField(read_only=True, default=None)
    rating_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = DriverProfile
        fields = [
            "id", "email", "full_name", "user_status",
            "vehicle_type", "vehicle_registration",
            "is_approved", "approved_at", "rejection_reason", "date_joined",
            "average_rating", "rating_count",
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


class StaffSerializer(serializers.ModelSerializer):
    """An admin-role account on the Team page: the super admin or a manager."""
    full_name = serializers.CharField(read_only=True)
    is_super_admin = serializers.BooleanField(source="is_superuser", read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name", "phone",
            "status", "is_super_admin", "date_joined", "last_login",
        ]
        read_only_fields = fields


class ManagerCreateSerializer(serializers.Serializer):
    """POST /admin/staff/ — the super admin adds a manager, who then sets their own password."""
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def create(self, validated_data):
        from .models import UserRole, UserStatus

        return User.objects.create_user(
            password=None,  # unusable until they follow their set-password link
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            is_staff=True,  # Django admin access, limited by ManagerPermissionBackend
            is_superuser=False,
            **validated_data,
        )
