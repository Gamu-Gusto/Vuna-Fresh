from rest_framework.permissions import BasePermission

from apps.users.permissions import IsSuperAdmin  # noqa: F401 — re-exported for payments views


class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "admin")


class IsAdminOrFarmer(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in ("admin", "farmer"))
