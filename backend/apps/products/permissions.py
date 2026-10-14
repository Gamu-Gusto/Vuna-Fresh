from rest_framework.permissions import BasePermission


class IsProductFarmer(BasePermission):
    """Allow write access only to the farmer who owns the product."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "farmer")

    def has_object_permission(self, request, view, obj):
        try:
            return obj.farmer == request.user.farmer_profile
        except AttributeError:
            return False


class IsAdminUser(BasePermission):
    """Allow access only to admin-role users."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "admin")


class IsProductFarmerOrAdmin(BasePermission):
    """Allow write access to the product's own farmer, or any admin."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in ("farmer", "admin"))

    def has_object_permission(self, request, view, obj):
        if request.user.role == "admin":
            return True
        try:
            return obj.farmer == request.user.farmer_profile
        except AttributeError:
            return False
