from django.db.models import Avg, Count, Q
from django.utils import timezone
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .admin_serializers import (
    AdminUserSerializer,
    ApprovalActionSerializer,
    DriverDocumentReviewSerializer,
    ManagerCreateSerializer,
    PendingDriverSerializer,
    PendingFarmerSerializer,
    StaffSerializer,
)
from .models import DocumentStatus, DriverDocument, DriverProfile, FarmerProfile, User, UserRole, UserStatus
from .permissions import IsAdminUser, IsSuperAdmin, is_super_admin


class FarmerApprovalViewSet(viewsets.GenericViewSet):
    """
    GET  /api/v1/admin/farmers/          — list all farmers (filter ?pending=true for unapproved)
    GET  /api/v1/admin/farmers/<id>/     — farmer detail
    POST /api/v1/admin/farmers/<id>/review/ — approve or reject
    """
    permission_classes = [IsAdminUser]
    serializer_class = PendingFarmerSerializer

    def get_queryset(self):
        qs = FarmerProfile.objects.select_related("user")
        if self.request.query_params.get("pending") == "true":
            qs = qs.filter(is_approved=False)
        return qs

    def list(self, request):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="review")
    def review(self, request, pk=None):
        profile = self.get_object()
        serializer = ApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data["action"] == "approve":
            profile.is_approved = True
            profile.approved_at = timezone.now()
            profile.approved_by = request.user
            profile.rejection_reason = ""
            profile.user.status = UserStatus.ACTIVE
            profile.save(update_fields=["is_approved", "approved_at", "approved_by", "rejection_reason"])
            profile.user.save(update_fields=["status"])
        else:
            profile.is_approved = False
            profile.rejection_reason = serializer.validated_data["reason"]
            profile.approved_by = None
            profile.approved_at = None
            profile.save(update_fields=["is_approved", "rejection_reason", "approved_by", "approved_at"])

        return Response(PendingFarmerSerializer(profile).data)


class DriverApprovalViewSet(viewsets.GenericViewSet):
    """
    GET  /api/v1/admin/drivers/           — list all drivers (filter ?pending=true for unapproved)
    GET  /api/v1/admin/drivers/<id>/      — driver detail
    POST /api/v1/admin/drivers/<id>/review/ — approve or reject
    """
    permission_classes = [IsAdminUser]
    serializer_class = PendingDriverSerializer

    def get_queryset(self):
        visible = ~Q(reviews__status="removed")
        qs = DriverProfile.objects.select_related("user").prefetch_related("documents").annotate(
            average_rating=Avg("reviews__rating", filter=visible),
            rating_count=Count("reviews", filter=visible),
        )
        if self.request.query_params.get("pending") == "true":
            qs = qs.filter(is_approved=False)
        return qs

    def list(self, request):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="review")
    def review(self, request, pk=None):
        profile = self.get_object()
        serializer = ApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data["action"] == "approve":
            # Only a complete application can be approved: 21+, consent given, and every
            # required document in with none rejected (see driver_verification.py)
            check = profile.verification_status()
            if not check["complete"]:
                problems = []
                if not check["old_enough"]:
                    problems.append("the driver isn't 21 or older, or has no date of birth")
                if not check["consent"]:
                    problems.append("the driver hasn't agreed to the document check")
                if check["missing"]:
                    problems.append(f"{len(check['missing'])} required document(s) not uploaded")
                if check["rejected"]:
                    problems.append(f"{len(check['rejected'])} document(s) need a new upload")
                return Response(
                    {"error": {"code": "bad_request", "message": "Can't approve yet: " + "; ".join(problems) + "."}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            now = timezone.now()
            profile.documents.filter(status=DocumentStatus.SUBMITTED).update(
                status=DocumentStatus.ACCEPTED, reviewed_by=request.user, reviewed_at=now,
            )
            profile.is_approved = True
            profile.approved_at = now
            profile.approved_by = request.user
            profile.rejection_reason = ""
            profile.rejected_at = None
            profile.user.status = UserStatus.ACTIVE
            profile.save(update_fields=["is_approved", "approved_at", "approved_by", "rejection_reason", "rejected_at"])
            profile.user.save(update_fields=["status"])
        else:
            profile.is_approved = False
            profile.rejection_reason = serializer.validated_data["reason"]
            profile.approved_by = None
            profile.approved_at = None
            # Starts the 30-day clock after which the documents are deleted
            profile.rejected_at = timezone.now()
            profile.save(update_fields=["is_approved", "rejection_reason", "approved_by", "approved_at", "rejected_at"])

        # Reload: the documents were prefetched before this change
        return Response(PendingDriverSerializer(self.get_object()).data)

    def _document(self, profile, doc_id):
        return DriverDocument.objects.filter(driver=profile, pk=doc_id).first()

    @action(detail=True, methods=["get"], url_path=r"documents/(?P<doc_id>\d+)/file")
    def document_file(self, request, pk=None, doc_id=None):
        """GET /admin/drivers/<id>/documents/<doc_id>/file/ — view one document (logged)."""
        from apps.privacy.models import DataAccessAuditLog
        from config.private_storage import serve_private_file

        profile = self.get_object()
        doc = self._document(profile, doc_id)
        if doc is None:
            return Response(
                {"error": {"code": "not_found", "message": "Document not found."}}, status=status.HTTP_404_NOT_FOUND,
            )
        DataAccessAuditLog.objects.create(
            user=profile.user, accessed_by=request.user,
            reason=f"Viewed driver document: {doc.get_doc_type_display()}",
        )
        return serve_private_file(doc.file, doc.original_name or f"{doc.doc_type}.pdf", doc.content_type)

    @action(detail=True, methods=["post"], url_path=r"documents/(?P<doc_id>\d+)/review")
    def document_review(self, request, pk=None, doc_id=None):
        """POST /admin/drivers/<id>/documents/<doc_id>/review/ — {action: accept|reject, note}."""
        profile = self.get_object()
        doc = self._document(profile, doc_id)
        if doc is None:
            return Response(
                {"error": {"code": "not_found", "message": "Document not found."}}, status=status.HTTP_404_NOT_FOUND,
            )
        serializer = DriverDocumentReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        accepted = serializer.validated_data["action"] == "accept"
        doc.status = DocumentStatus.ACCEPTED if accepted else DocumentStatus.REJECTED
        doc.review_note = "" if accepted else serializer.validated_data["note"].strip()
        doc.reviewed_by = request.user
        doc.reviewed_at = timezone.now()
        doc.save(update_fields=["status", "review_note", "reviewed_by", "reviewed_at"])
        if not accepted:
            from apps.notifications.models import NotificationCategory
            from apps.notifications.services.dispatcher import notify

            notify(
                profile.user, "driver_document_rejected",
                f"Please upload a new {doc.get_doc_type_display().lower()}: {doc.review_note}",
                NotificationCategory.ORDER_UPDATES, link="/driver/documents",
            )
        # Reload: the documents were prefetched before this change
        return Response(PendingDriverSerializer(self.get_object()).data)


class UserManagementViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET  /api/v1/admin/users/                  — list all users (?role=farmer&status=pending)
    GET  /api/v1/admin/users/<id>/             — user detail
    POST /api/v1/admin/users/<id>/deactivate/  — set status to 'deactivated'
    """
    permission_classes = [IsAdminUser]
    serializer_class = AdminUserSerializer

    def get_queryset(self):
        qs = User.objects.all()
        role = self.request.query_params.get("role")
        user_status = self.request.query_params.get("status")
        if role:
            qs = qs.filter(role=role)
        if user_status:
            qs = qs.filter(status=user_status)
        return qs

    @action(detail=True, methods=["post"], url_path="deactivate")
    def deactivate(self, request, pk=None):
        user = self.get_object()
        if user == request.user:
            return Response(
                {"error": {"code": "forbidden", "message": "You cannot deactivate your own account."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        if user.role == UserRole.ADMIN and not is_super_admin(request.user):
            return Response(
                {"error": {"code": "forbidden", "message": "Only the super admin can deactivate admin accounts."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        user.status = UserStatus.DEACTIVATED
        user.is_active = False
        user.save(update_fields=["status", "is_active"])
        return Response(AdminUserSerializer(user).data)


class StaffViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    Super admin only — the admin team.

    GET  /api/v1/admin/staff/                        — every admin-role account
    POST /api/v1/admin/staff/                        — add a manager {email, first_name, last_name, phone?};
                                                        returns the account and a one-time set_password_link
    POST /api/v1/admin/staff/<id>/deactivate/        — deactivate a manager
    POST /api/v1/admin/staff/<id>/reactivate/        — reactivate a manager
    POST /api/v1/admin/staff/<id>/set_password_link/ — a fresh link, e.g. if the first one expired

    Managers can do everything else an admin can, but never this, and never pay farmers.
    """
    permission_classes = [IsSuperAdmin]
    serializer_class = StaffSerializer

    def get_queryset(self):
        return User.objects.filter(role=UserRole.ADMIN).order_by("-is_superuser", "first_name", "email")

    def create(self, request, *args, **kwargs):
        serializer = ManagerCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        link = self._send_link(user, invited_by=request.user)
        return Response(
            {"staff": StaffSerializer(user).data, "set_password_link": link},
            status=status.HTTP_201_CREATED,
        )

    def _refuse_super_admin(self, user):
        if user.is_superuser:
            return Response(
                {"error": {"code": "forbidden", "message": "The super admin account can't be changed here."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    @action(detail=True, methods=["post"], url_path="deactivate")
    def deactivate(self, request, pk=None):
        user = self.get_object()
        if (refused := self._refuse_super_admin(user)):
            return refused
        user.status = UserStatus.DEACTIVATED
        user.is_active = False
        user.save(update_fields=["status", "is_active"])
        return Response(StaffSerializer(user).data)

    @action(detail=True, methods=["post"], url_path="reactivate")
    def reactivate(self, request, pk=None):
        user = self.get_object()
        if (refused := self._refuse_super_admin(user)):
            return refused
        user.status = UserStatus.ACTIVE
        user.is_active = True
        user.save(update_fields=["status", "is_active"])
        return Response(StaffSerializer(user).data)

    @action(detail=True, methods=["post"], url_path="set_password_link")
    def set_password_link(self, request, pk=None):
        user = self.get_object()
        if (refused := self._refuse_super_admin(user)):
            return refused
        if not user.is_active:
            return Response(
                {"error": {"code": "bad_request", "message": "Reactivate this manager before sending a new link."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"set_password_link": self._send_link(user, invited_by=request.user)})

    def _send_link(self, user, invited_by):
        """Email the manager their link (written to the log if email isn't set up) and return it."""
        import logging

        from django.core.mail import send_mail

        from .password_links import set_password_link

        link = set_password_link(user, portal="admin")
        body = (
            f"Hi {user.first_name},\n\n"
            f"{invited_by.first_name or 'The Vuna Fresh super admin'} has given you a manager account on "
            f"Vuna Fresh. Choose your password here:\n\n{link}\n\n"
            "The link works once and expires in 3 days. Then log in on the admin log-in page "
            "with this email address.\n\n"
            "Vuna Fresh"
        )
        try:
            send_mail("Your Vuna Fresh manager account", body, None, [user.email])
        except Exception:
            logging.getLogger(__name__).exception("Manager invitation email failed for user #%s", user.pk)
        return link
