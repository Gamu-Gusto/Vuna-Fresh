from django.db.models import Avg, Count, Q
from django.utils import timezone
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .admin_serializers import (
    AdminUserSerializer,
    ApprovalActionSerializer,
    ManagerCreateSerializer,
    PendingDriverSerializer,
    PendingFarmerSerializer,
    StaffSerializer,
)
from .models import DriverProfile, FarmerProfile, User, UserRole, UserStatus
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
        qs = DriverProfile.objects.select_related("user").annotate(
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

        return Response(PendingDriverSerializer(profile).data)


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
