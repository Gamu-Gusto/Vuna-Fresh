"""
Role-based DRF permission classes. Use these on ViewSets instead of
manual role checks in view logic.

Usage:
    class MyViewSet(ModelViewSet):
        permission_classes = [IsBuyer]
"""
from rest_framework.permissions import BasePermission


class IsBuyer(BasePermission):
    """Allow access only to users with the 'customer' role (i.e. buyers)."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "customer"
        )


class IsFarmer(BasePermission):
    """Allow access only to approved farmers."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.role == "farmer"):
            return False
        try:
            return request.user.farmer_profile.is_approved
        except AttributeError:
            return False


class IsFarmerAccount(BasePermission):
    """Allow any authenticated farmer-role user, regardless of approval
    status — unlike IsFarmer, this does NOT require is_approved. Used only
    for a farmer to read/update their own profile so pending/rejected
    farmers can still see their own application status."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "farmer"
        )


class IsDriver(BasePermission):
    """Allow access only to approved drivers."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.role == "driver"):
            return False
        try:
            return request.user.driver_profile.is_approved
        except AttributeError:
            return False


class IsAdminUser(BasePermission):
    """Allow access only to users with the 'admin' role."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "admin"
        )


class IsAdminOrReadOnly(BasePermission):
    """Allow full access to admins; read-only to authenticated non-admins."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return request.user.role == "admin"
