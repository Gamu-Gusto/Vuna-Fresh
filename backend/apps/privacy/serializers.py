from django.utils import timezone
from rest_framework import serializers

from .models import (
    ConsentRecord,
    ConsentType,
    DataAccessAuditLog,
    DataAccessRequest,
    DataAccessRequestStatus,
)


class ConsentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentRecord
        fields = ["id", "consent_type", "granted", "granted_at", "revoked_at"]
        read_only_fields = ["id", "granted_at", "revoked_at"]


class ConsentUpdateSerializer(serializers.Serializer):
    """
    Accepts a list of consent updates.  Each entry specifies a consent_type and
    whether the user is granting or revoking it.

    Input:
        [
            {"consent_type": "marketing", "granted": true},
            {"consent_type": "cookies", "granted": false}
        ]
    """
    consent_type = serializers.ChoiceField(choices=ConsentType.choices)
    granted = serializers.BooleanField()


class DataAccessRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataAccessRequest
        fields = ["id", "request_type", "status", "requested_at", "completed_at"]
        read_only_fields = ["id", "status", "requested_at", "completed_at"]

    def validate_request_type(self, value):
        user = self.context["request"].user
        if DataAccessRequest.objects.filter(
            user=user, request_type=value, status=DataAccessRequestStatus.PENDING,
        ).exists():
            raise serializers.ValidationError("You already have a pending request of this type.")
        return value

    def create(self, validated_data):
        # NOTE: Actual fulfillment (data export, deletion) is a manual admin process.
        # This endpoint only creates the request record with status 'pending'.
        # A future task will add tooling for admins to export/delete user data and
        # mark the request as completed. Do not automate fulfillment here.
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class DataAccessRequestAdminSerializer(serializers.ModelSerializer):
    """Admin-only serializer that also allows status updates."""
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = DataAccessRequest
        fields = ["id", "user_email", "request_type", "status", "requested_at", "completed_at"]
        read_only_fields = ["id", "user_email", "request_type", "requested_at"]

    def validate_status(self, value):
        if value == DataAccessRequestStatus.PENDING:
            raise serializers.ValidationError("Cannot revert a request back to 'pending'.")
        return value

    def update(self, instance, validated_data):
        if "status" in validated_data and validated_data["status"] in (
            DataAccessRequestStatus.COMPLETED, DataAccessRequestStatus.DENIED
        ):
            validated_data["completed_at"] = timezone.now()
        return super().update(instance, validated_data)


class DataAccessAuditLogSerializer(serializers.ModelSerializer):
    accessed_by_email = serializers.SerializerMethodField()

    class Meta:
        model = DataAccessAuditLog
        fields = ["id", "accessed_by_email", "reason", "accessed_at"]

    def get_accessed_by_email(self, obj):
        return obj.accessed_by.email if obj.accessed_by else "system"
