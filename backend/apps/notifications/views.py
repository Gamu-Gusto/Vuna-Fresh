from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification, NotificationPreference
from .serializers import (
    NotificationPreferenceSerializer,
    NotificationPreferenceUpdateSerializer,
    NotificationSerializer,
)


class NotificationPreferenceViewSet(viewsets.GenericViewSet):
    """
    GET  /api/v1/notifications/preferences/         — list own preferences
    POST /api/v1/notifications/preferences/update/  — update one or more preferences
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        prefs = NotificationPreference.objects.filter(user=request.user)
        return Response(NotificationPreferenceSerializer(prefs, many=True).data)

    @action(detail=False, methods=["post"], url_path="update")
    def update_preferences(self, request):
        if not isinstance(request.data, list):
            return Response(
                {"error": {"code": "validation_error", "message": "Expected a list of preference updates."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = NotificationPreferenceUpdateSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        results = []
        for item in serializer.validated_data:
            pref, _ = NotificationPreference.objects.get_or_create(
                user=request.user,
                channel=item["channel"],
                category=item["category"],
                defaults={"enabled": item["enabled"]},
            )
            pref.enabled = item["enabled"]
            pref.save(update_fields=["enabled"])
            results.append(pref)

        return Response(NotificationPreferenceSerializer(results, many=True).data)


class NotificationViewSet(viewsets.GenericViewSet):
    """
    GET  /api/v1/notifications/                — list own notifications
    GET  /api/v1/notifications/unread_count/   — {count} for the nav bell
    POST /api/v1/notifications/<id>/mark_read/  — mark one as read
    POST /api/v1/notifications/mark_all_read/   — mark every unread one as read
    """
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def list(self, request):
        notifications = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(notifications)
        serializer = NotificationSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=["get"], url_path="unread_count")
    def unread_count(self, request):
        return Response({"count": self.get_queryset().filter(read=False).count()})

    @action(detail=False, methods=["post"], url_path="mark_all_read")
    def mark_all_read(self, request):
        updated = self.get_queryset().filter(read=False).update(read=True)
        return Response({"updated": updated})

    @action(detail=True, methods=["post"], url_path="mark_read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        if not notification.read:
            notification.read = True
            notification.save(update_fields=["read"])
        return Response(NotificationSerializer(notification).data)
