from rest_framework.permissions import BasePermission


class IsBuyer(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "customer")


class IsFarmer(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "farmer")


class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "admin")


class IsReviewOwner(BasePermission):
    """Object-level: the buyer who wrote the review, or any owner/buyer-role
    member of that business account (viewers are read-only)."""

    def has_object_permission(self, request, view, obj):
        from apps.buyers.resolvers import user_can_act_for_buyer_profile
        return user_can_act_for_buyer_profile(request.user, obj.buyer, require_write=True)
