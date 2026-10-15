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


def is_super_admin(user):
    """
    The super admin is an admin-role account that is also a Django superuser
    (the first admin, created with createsuperuser). Every other admin-role
    account is a manager: it can do everything except manage admin accounts
    and pay farmers.
    """
    return bool(user and user.is_authenticated and user.role == "admin" and user.is_superuser)


class IsSuperAdmin(BasePermission):
    """Allow access only to the super admin (see is_super_admin)."""

    def has_permission(self, request, view):
        return is_super_admin(request.user)


class IsAdminOrReadOnly(BasePermission):
    """Allow full access to admins; read-only to authenticated non-admins."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return request.user.role == "admin"
