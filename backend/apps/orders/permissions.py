from rest_framework.permissions import BasePermission


class IsBuyer(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "customer")


class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "admin")


class IsOrderBuyer(BasePermission):
    """Object-level: only the buyer who placed the order."""

    def has_object_permission(self, request, view, obj):
        try:
            return obj.buyer == request.user.buyer_profile
        except AttributeError:
            return False
