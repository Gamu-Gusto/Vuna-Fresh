from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ConsentRecord, DataAccessAuditLog, DataAccessRequest
from .permissions import IsAdminUser
from .serializers import (
    ConsentRecordSerializer,
    ConsentUpdateSerializer,
    DataAccessAuditLogSerializer,
    DataAccessRequestAdminSerializer,
    DataAccessRequestSerializer,
)


class ConsentViewSet(viewsets.GenericViewSet):
    """
    GET  /api/v1/privacy/consent/        — list own consent records
    POST /api/v1/privacy/consent/update/ — grant or revoke one or more consent types
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        records = ConsentRecord.objects.filter(user=request.user)
        serializer = ConsentRecordSerializer(records, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="update")
    def update_consent(self, request):
        # Accept a list of {"consent_type": ..., "granted": ...}
        if not isinstance(request.data, list):
            return Response(
                {"error": {"code": "validation_error", "message": "Expected a list of consent updates."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ConsentUpdateSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        results = []
        for item in serializer.validated_data:
            record, _ = ConsentRecord.objects.get_or_create(
                user=request.user,
                consent_type=item["consent_type"],
            )
            if item["granted"]:
                record.grant()
            else:
                record.revoke()
            results.append(record)

        return Response(ConsentRecordSerializer(results, many=True).data)


class DataAccessRequestViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    POST /api/v1/privacy/data-requests/         — submit a request (any authenticated user)
    GET  /api/v1/privacy/data-requests/         — list own requests (or all, if admin)
    GET  /api/v1/privacy/data-requests/<id>/    — detail (own request, or admin)
    PATCH /api/v1/privacy/data-requests/<id>/   — update status (admin only)
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == "admin":
            return DataAccessRequest.objects.select_related("user").all()
        return DataAccessRequest.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.request.user.role == "admin" and self.action in ("list", "retrieve", "partial_update"):
            return DataAccessRequestAdminSerializer
        return DataAccessRequestSerializer

    def retrieve(self, request, pk=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def partial_update(self, request, pk=None):
        if request.user.role != "admin":
            return Response(
                {"error": {"code": "forbidden", "message": "Only admins can update request status."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance = self.get_object()
        serializer = DataAccessRequestAdminSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class DataAccessAuditLogViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET /api/v1/privacy/audit-log/ — view own audit log (read-only)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = DataAccessAuditLogSerializer

    def get_queryset(self):
        # Users see only their own log; admin sees all
        if self.request.user.role == "admin":
            return DataAccessAuditLog.objects.select_related("user", "accessed_by").all()
        return DataAccessAuditLog.objects.filter(user=self.request.user).select_related("accessed_by")
