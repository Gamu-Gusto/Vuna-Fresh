from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.buyers.resolvers import (
    get_accessible_buyer_profiles,
    resolve_active_buyer_profile,
    user_can_act_for_buyer_profile,
)

from .models import Subscription, SubscriptionStatus
from .permissions import IsBuyer
from .serializers import SubscriptionCreateSerializer, SubscriptionSerializer


class SubscriptionViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    POST /api/v1/subscriptions/             — create a subscription
    GET  /api/v1/subscriptions/             — list own subscriptions
    GET  /api/v1/subscriptions/<id>/        — subscription detail
    POST /api/v1/subscriptions/<id>/pause/  — pause
    POST /api/v1/subscriptions/<id>/resume/ — resume
    POST /api/v1/subscriptions/<id>/cancel/ — cancel

    Business account members see/manage subscriptions across every account
    they belong to (own + memberships); creating one defaults to the user's
    own account, or a specific one via `X-Buyer-Account: <id>` (viewers can't
    create/pause/resume/cancel — see apps.buyers.resolvers).
    """
    permission_classes = [IsAuthenticated, IsBuyer]

    def get_queryset(self):
        accessible_ids = [p.id for p in get_accessible_buyer_profiles(self.request.user)]
        return Subscription.objects.select_related("product", "buyer__user").filter(
            buyer_id__in=accessible_ids
        )

    def get_serializer_class(self):
        if self.action == "create":
            return SubscriptionCreateSerializer
        return SubscriptionSerializer

    def create(self, request, *args, **kwargs):
        buyer = resolve_active_buyer_profile(request, require_write=True)
        if buyer is None:
            return Response(
                {"error": {"code": "forbidden", "message": "You don't have write access to this buyer account."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(data=request.data, context={"request": request, "buyer": buyer})
        serializer.is_valid(raise_exception=True)
        subscription = serializer.save()
        return Response(SubscriptionSerializer(subscription).data, status=status.HTTP_201_CREATED)

    def _forbidden_response(self):
        return Response(
            {"error": {"code": "forbidden", "message": "You don't have write access to this buyer account."}},
            status=status.HTTP_403_FORBIDDEN,
        )

    @action(detail=True, methods=["post"], url_path="pause")
    def pause(self, request, pk=None):
        subscription = self.get_object()
        if not user_can_act_for_buyer_profile(request.user, subscription.buyer, require_write=True):
            return self._forbidden_response()
        if subscription.status != SubscriptionStatus.ACTIVE:
            return Response(
                {"error": {"code": "bad_request", "message": "Only active subscriptions can be paused."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        subscription.status = SubscriptionStatus.PAUSED
        subscription.save(update_fields=["status"])
        return Response(SubscriptionSerializer(subscription).data)

    @action(detail=True, methods=["post"], url_path="resume")
    def resume(self, request, pk=None):
        subscription = self.get_object()
        if not user_can_act_for_buyer_profile(request.user, subscription.buyer, require_write=True):
            return self._forbidden_response()
        if subscription.status != SubscriptionStatus.PAUSED:
            return Response(
                {"error": {"code": "bad_request", "message": "Only paused subscriptions can be resumed."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.save(update_fields=["status"])
        return Response(SubscriptionSerializer(subscription).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        subscription = self.get_object()
        if not user_can_act_for_buyer_profile(request.user, subscription.buyer, require_write=True):
            return self._forbidden_response()
        if subscription.status == SubscriptionStatus.CANCELLED:
            return Response(
                {"error": {"code": "bad_request", "message": "This subscription is already cancelled."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.save(update_fields=["status"])
        return Response(SubscriptionSerializer(subscription).data)
