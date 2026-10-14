from django.utils import timezone
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import BusinessApprovalStatus, BusinessBuyerDetails, BuyerAccountMember, BuyerAccountMemberRole
from .permissions import IsAdminUser
from .serializers import (
    BuyerAccountMemberAddSerializer,
    BuyerAccountMemberSerializer,
    BusinessApprovalActionSerializer,
    BusinessBuyerDetailsSerializer,
    BusinessBuyerSignupSerializer,
)


class BusinessBuyerSignupView(generics.CreateAPIView):
    """POST /api/v1/buyers/business/signup/ — register a new business buyer account."""
    permission_classes = [AllowAny]
    serializer_class = BusinessBuyerSignupSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        business_details = serializer.save()
        return Response(
            BusinessBuyerDetailsSerializer(business_details).data,
            status=status.HTTP_201_CREATED,
        )


class BusinessBuyerApprovalViewSet(viewsets.GenericViewSet):
    """
    GET  /api/v1/buyers/admin/business/             — list (filter ?pending=true)
    GET  /api/v1/buyers/admin/business/<id>/        — detail
    POST /api/v1/buyers/admin/business/<id>/review/ — approve or suspend
    """
    permission_classes = [IsAdminUser]
    serializer_class = BusinessBuyerDetailsSerializer

    def get_queryset(self):
        qs = BusinessBuyerDetails.objects.select_related("buyer__user", "billing_address")
        if self.request.query_params.get("pending") == "true":
            qs = qs.filter(approval_status=BusinessApprovalStatus.PENDING)
        return qs

    def list(self, request):
        return Response(self.get_serializer(self.get_queryset(), many=True).data)

    def retrieve(self, request, pk=None):
        return Response(self.get_serializer(self.get_object()).data)

    @action(detail=True, methods=["post"], url_path="review")
    def review(self, request, pk=None):
        details = self.get_object()
        serializer = BusinessApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data["action"] == "approve":
            details.approval_status = BusinessApprovalStatus.ACTIVE
            details.approved_by = request.user
            details.approved_at = timezone.now()
            details.rejection_reason = ""
        else:
            details.approval_status = BusinessApprovalStatus.SUSPENDED
            details.rejection_reason = serializer.validated_data["reason"]
            details.approved_by = None
            details.approved_at = None

        details.save(update_fields=["approval_status", "rejection_reason", "approved_by", "approved_at"])
        return Response(BusinessBuyerDetailsSerializer(details).data)


class MyBusinessDetailsView(generics.RetrieveAPIView):
    """
    GET /api/v1/buyers/me/business/ — the authenticated business buyer's own
    BusinessBuyerDetails (approval_status, rejection_reason, etc). Lets a
    business buyer tell pending/active/suspended apart after signup/login,
    same purpose FarmerProfileView already serves for farmers.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = BusinessBuyerDetailsSerializer

    def get_object(self):
        buyer_profile = getattr(self.request.user, "buyer_profile", None)
        if buyer_profile is None or buyer_profile.buyer_type != "business":
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("This account has no business buyer details.")
        return buyer_profile.business_details


class BuyerAccountMemberViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET    /api/v1/buyers/members/       — list members of my business account (owner only)
    POST   /api/v1/buyers/members/       — add a member by email (owner only)
    DELETE /api/v1/buyers/members/<id>/  — remove a member (owner only)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = BuyerAccountMemberSerializer

    def _owned_buyer_profile(self, request):
        """The business BuyerProfile the requesting user owns, or None."""
        buyer_profile = getattr(request.user, "buyer_profile", None)
        if buyer_profile is None or buyer_profile.buyer_type != "business":
            return None
        is_owner = BuyerAccountMember.objects.filter(
            buyer_profile=buyer_profile, user=request.user, role=BuyerAccountMemberRole.OWNER
        ).exists()
        return buyer_profile if is_owner else None

    def get_queryset(self):
        buyer_profile = self._owned_buyer_profile(self.request)
        if buyer_profile is None:
            return BuyerAccountMember.objects.none()
        return BuyerAccountMember.objects.filter(buyer_profile=buyer_profile).select_related("user")

    def create(self, request, *args, **kwargs):
        buyer_profile = self._owned_buyer_profile(request)
        if buyer_profile is None:
            return Response(
                {"error": {"code": "forbidden", "message": "Only a business account owner can add members."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = BuyerAccountMemberAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        member, created = BuyerAccountMember.objects.get_or_create(
            buyer_profile=buyer_profile,
            user=serializer._user,
            defaults={"role": serializer.validated_data["role"]},
        )
        if not created:
            return Response(
                {"error": {"code": "bad_request", "message": "This user is already a member of your account."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(BuyerAccountMemberSerializer(member).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        buyer_profile = self._owned_buyer_profile(request)
        if buyer_profile is None:
            return Response(
                {"error": {"code": "forbidden", "message": "Only a business account owner can remove members."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance = self.get_object()
        if instance.role == BuyerAccountMemberRole.OWNER:
            return Response(
                {"error": {"code": "bad_request", "message": "Cannot remove the account owner."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
