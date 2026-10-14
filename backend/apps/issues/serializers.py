from django.utils import timezone
from rest_framework import serializers

from .models import Issue, IssueAttachment, IssueMessage, IssueRating, IssueStatus


class IssueAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = IssueAttachment
        fields = ["id", "file_url", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]


class IssueMessageSerializer(serializers.ModelSerializer):
    """Read serializer for messages in the thread."""
    sender_email = serializers.EmailField(source="sender.email", read_only=True)
    sender_role = serializers.CharField(source="sender.role", read_only=True)

    class Meta:
        model = IssueMessage
        fields = ["id", "sender", "sender_email", "sender_role", "message", "sent_at"]
        read_only_fields = fields


class IssueMessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = IssueMessage
        fields = ["message"]

    def create(self, validated_data):
        validated_data["issue"] = self.context["issue"]
        validated_data["sender"] = self.context["request"].user
        return super().create(validated_data)


class IssueRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = IssueRating
        fields = ["id", "rating", "comment", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        issue = self.context["issue"]
        if issue.status not in (IssueStatus.RESOLVED, IssueStatus.CLOSED):
            raise serializers.ValidationError(
                "You can only rate an issue once it's resolved or closed."
            )
        if hasattr(issue, "rating"):
            raise serializers.ValidationError("This issue has already been rated.")
        return attrs

    def create(self, validated_data):
        validated_data["issue"] = self.context["issue"]
        return super().create(validated_data)


class IssueSerializer(serializers.ModelSerializer):
    """Read serializer for retrieve — includes the full thread, attachments, and rating."""
    reporter_email = serializers.EmailField(source="reported_by.email", read_only=True)
    attachments = IssueAttachmentSerializer(many=True, read_only=True)
    messages = IssueMessageSerializer(many=True, read_only=True)
    rating = IssueRatingSerializer(read_only=True)

    class Meta:
        model = Issue
        fields = [
            "id",
            "reported_by",
            "reporter_email",
            "order",
            "category",
            "description",
            "status",
            "resolution_type",
            "attachments",
            "messages",
            "rating",
            "created_at",
            "resolved_at",
        ]
        read_only_fields = [
            "id", "reported_by", "reporter_email", "status", "resolution_type",
            "attachments", "messages", "rating", "created_at", "resolved_at",
        ]


class IssueListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views — no nested thread/attachments."""
    reporter_email = serializers.EmailField(source="reported_by.email", read_only=True)

    class Meta:
        model = Issue
        fields = [
            "id", "reported_by", "reporter_email", "order", "category",
            "description", "status", "resolution_type", "created_at", "resolved_at",
        ]
        read_only_fields = fields


class IssueCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Issue
        fields = ["id", "order", "category", "description"]
        read_only_fields = ["id"]

    def validate_order(self, value):
        if value is None:
            return value

        user = self.context["request"].user
        if user.role == "admin":
            return value
        if user.role == "customer":
            try:
                if value.buyer == user.buyer_profile:
                    return value
            except AttributeError:
                pass
        elif user.role == "driver":
            try:
                if value.driver == user.driver_profile:
                    return value
            except AttributeError:
                pass
        elif user.role == "farmer":
            try:
                if value.items.filter(farmer=user.farmer_profile).exists():
                    return value
            except AttributeError:
                pass

        raise serializers.ValidationError("This order does not belong to you.")

    def create(self, validated_data):
        validated_data["reported_by"] = self.context["request"].user
        return super().create(validated_data)


class IssueStatusUpdateSerializer(serializers.ModelSerializer):
    """Admin-only — moves an issue between open/in_progress/resolved/closed and sets resolution_type."""

    class Meta:
        model = Issue
        fields = ["status", "resolution_type"]

    def update(self, instance, validated_data):
        new_status = validated_data.get("status", instance.status)
        instance.status = new_status
        instance.resolution_type = validated_data.get("resolution_type", instance.resolution_type)

        if new_status in (IssueStatus.RESOLVED, IssueStatus.CLOSED):
            if instance.resolved_at is None:
                instance.resolved_at = timezone.now()
        else:
            instance.resolved_at = None

        instance.save(update_fields=["status", "resolution_type", "resolved_at"])
        return instance
