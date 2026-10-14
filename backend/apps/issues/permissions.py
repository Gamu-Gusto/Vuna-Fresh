from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "admin")


class IsIssueOwner(BasePermission):
    """Object-level: only the user who reported the issue, or an admin."""

    def has_object_permission(self, request, view, obj):
        if request.user.role == "admin":
            return True
        return obj.reported_by_id == request.user.id
