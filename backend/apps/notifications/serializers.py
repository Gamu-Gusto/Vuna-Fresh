from rest_framework import serializers

from .models import Notification, NotificationCategory, NotificationChannel, NotificationPreference


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ["id", "channel", "category", "enabled"]
        read_only_fields = ["id", "channel", "category"]


class NotificationPreferenceUpdateSerializer(serializers.Serializer):
    """
    Accepts a list of preference updates.

    Input:
        [
            {"channel": "email", "category": "marketing", "enabled": true},
            {"channel": "sms", "category": "order_updates", "enabled": false}
        ]
    """
    channel = serializers.ChoiceField(choices=NotificationChannel.choices)
    category = serializers.ChoiceField(choices=NotificationCategory.choices)
    enabled = serializers.BooleanField()


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "type", "message", "read", "created_at"]
        read_only_fields = fields
