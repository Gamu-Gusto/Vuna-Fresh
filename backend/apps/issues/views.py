from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Issue
from .notifications import notify_issue_created, notify_issue_message, notify_issue_status
from .permissions import IsAdminUser, IsIssueOwner
from .serializers import (
    IssueAttachmentSerializer,
    IssueCreateSerializer,
    IssueListSerializer,
    IssueMessageCreateSerializer,
    IssueMessageSerializer,
    IssueRatingSerializer,
    IssueSerializer,
    IssueStatusUpdateSerializer,
)


class IssueViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    POST  /api/v1/issues/                   — report an issue (order-linked or platform-level)
    GET   /api/v1/issues/                   — list own issues (admin: all, ?status=, ?category=)
    GET   /api/v1/issues/<id>/              — issue detail incl. thread/attachments/rating
    POST  /api/v1/issues/<id>/messages/     — post a message to the thread (owner or admin)
    POST  /api/v1/issues/<id>/attachments/  — attach a file URL (owner)
    POST  /api/v1/issues/<id>/rate/         — rate a resolved/closed issue (owner)
    PATCH /api/v1/issues/<id>/set_status/   — admin: update status/resolution_type
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Issue.objects.select_related("reported_by", "order")

        if self.action == "retrieve":
            qs = qs.prefetch_related("attachments", "messages__sender")

        if user.role == "admin":
            if self.action == "list":
                status_param = self.request.query_params.get("status")
                if status_param:
                    qs = qs.filter(status=status_param)
                category_param = self.request.query_params.get("category")
                if category_param:
                    qs = qs.filter(category=category_param)
            return qs

        return qs.filter(reported_by=user)

    def get_serializer_class(self):
        if self.action == "create":
            return IssueCreateSerializer
        if self.action == "list":
            return IssueListSerializer
        return IssueSerializer

    def get_permissions(self):
        if self.action == "set_status":
            return [IsAuthenticated(), IsAdminUser()]
        if self.action in ("retrieve", "add_message", "add_attachment", "rate"):
            return [IsAuthenticated(), IsIssueOwner()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        issue = serializer.save()
        notify_issue_created(issue)
        return Response(
            IssueSerializer(issue, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="messages")
    def add_message(self, request, pk=None):
        issue = self.get_object()
        serializer = IssueMessageCreateSerializer(
            data=request.data, context={"request": request, "issue": issue}
        )
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        notify_issue_message(issue, message)
        return Response(IssueMessageSerializer(message).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="attachments")
    def add_attachment(self, request, pk=None):
        issue = self.get_object()
        serializer = IssueAttachmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(issue=issue)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="rate")
    def rate(self, request, pk=None):
        issue = self.get_object()
        serializer = IssueRatingSerializer(data=request.data, context={"issue": issue})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch"], url_path="set_status")
    def set_status(self, request, pk=None):
        issue = self.get_object()
        previous_status = issue.status
        serializer = IssueStatusUpdateSerializer(issue, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        issue = serializer.save()
        if issue.status != previous_status:
            notify_issue_status(issue)
        return Response(IssueSerializer(issue, context=self.get_serializer_context()).data)
