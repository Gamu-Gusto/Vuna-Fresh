from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.buyers.resolvers import (
    get_accessible_buyer_profiles,
    resolve_active_buyer_profile,
)

from .models import Cart, CartItem, CartStatus, Invoice, Order
from .notifications import notify_driver_assigned, notify_order_placed
from .permissions import IsAdminUser, IsBuyer
from .serializers import (
    CartItemAddSerializer,
    CartItemSerializer,
    CartItemUpdateSerializer,
    CartSerializer,
    CheckoutSerializer,
    DriverAssignSerializer,
    InvoiceSerializer,
    InvoiceStatusUpdateSerializer,
    OrderSerializer,
    OrderStatusUpdateSerializer,
    PickupDetailSerializer,
)


class CartViewSet(viewsets.GenericViewSet):
    """
    GET  /api/v1/cart/           — view active cart (creates one if none exists)
    POST /api/v1/cart/add_item/  — add a product to the cart

    A business account's members share one cart. By default this acts on the
    requesting user's own BuyerProfile; sending `X-Buyer-Account: <id>` acts on
    a business account they're a member of instead (see apps.buyers.resolvers).
    'viewer' members can view the cart but not modify it.
    """
    permission_classes = [IsAuthenticated, IsBuyer]

    def _get_or_create_active_cart(self, request, require_write):
        buyer = resolve_active_buyer_profile(request, require_write=require_write)
        if buyer is None:
            return None
        cart, _ = Cart.objects.get_or_create(buyer=buyer, status=CartStatus.ACTIVE)
        return cart

    def list(self, request):
        cart = self._get_or_create_active_cart(request, require_write=False)
        if cart is None:
            return Response(
                {"error": {"code": "forbidden", "message": "You don't have access to this buyer account."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="add_item")
    def add_item(self, request):
        serializer = CartItemAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart = self._get_or_create_active_cart(request, require_write=True)
        if cart is None:
            return Response(
                {"error": {"code": "forbidden", "message": "You don't have write access to this buyer account."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        product = serializer._product
        quantity = serializer.validated_data["quantity"]
        unit_price = serializer._unit_price
        surplus_listing = serializer._surplus_listing

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"price_at_add": unit_price, "quantity": quantity, "surplus_listing": surplus_listing},
        )
        if not created:
            # Product already in cart — update quantity and re-snapshot price
            item.quantity = quantity
            item.price_at_add = unit_price
            item.surplus_listing = surplus_listing
            item.save(update_fields=["quantity", "price_at_add", "surplus_listing"])

        return Response(CartItemSerializer(item).data, status=status.HTTP_200_OK)


class CartItemViewSet(
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    PATCH  /api/v1/cart/items/<id>/  — update quantity
    DELETE /api/v1/cart/items/<id>/  — remove item
    """
    permission_classes = [IsAuthenticated, IsBuyer]
    serializer_class = CartItemUpdateSerializer

    def get_queryset(self):
        buyer = resolve_active_buyer_profile(self.request, require_write=True)
        if buyer is None:
            return CartItem.objects.none()
        return CartItem.objects.filter(cart__buyer=buyer, cart__status=CartStatus.ACTIVE)


class OrderViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    POST /api/v1/orders/                      — checkout (customer)
    GET  /api/v1/orders/                      — list orders (role-filtered; admin: ?status=a,b&has_driver=)
    GET  /api/v1/orders/<id>/                 — order detail
    POST /api/v1/orders/<id>/update_status/   — advance order status
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Order.objects.select_related(
            "buyer__user", "delivery_address", "driver__user", "driver_review"
        ).prefetch_related(
            "items__product", "items__farmer", "status_history__changed_by", "transactions__deposit_proofs",
        )

        if user.role == "customer":
            # Shows orders across every buyer account this user can access
            # (their own + any business accounts they're a member of), unless
            # X-Buyer-Account narrows it to one specific account.
            if self.request.headers.get("X-Buyer-Account"):
                buyer = resolve_active_buyer_profile(self.request, require_write=False)
                if buyer is None:
                    return qs.none()
                return qs.filter(buyer=buyer)
            accessible_ids = [p.id for p in get_accessible_buyer_profiles(user)]
            return qs.filter(buyer_id__in=accessible_ids)
        if user.role == "farmer":
            # Farmers only see an order once it's released (paid, or on credit)
            return qs.filter(items__farmer=user.farmer_profile).released().distinct()
        if user.role == "driver":
            return qs.filter(driver=user.driver_profile)

        # admin sees all, optionally narrowed for the deliveries board:
        # ?status=ready_for_pickup,out_for_delivery and ?has_driver=true|false
        statuses = [s for s in self.request.query_params.get("status", "").split(",") if s]
        if statuses:
            qs = qs.filter(status__in=statuses)
        has_driver = self.request.query_params.get("has_driver")
        if has_driver in ("true", "false"):
            qs = qs.filter(driver__isnull=has_driver == "false")
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return CheckoutSerializer
        if self.action == "update_status":
            return OrderStatusUpdateSerializer
        return OrderSerializer

    def create(self, request, *args, **kwargs):
        if request.user.role != "customer":
            return Response(
                {"error": {"code": "forbidden", "message": "Only customers can place orders."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        buyer = resolve_active_buyer_profile(request, require_write=True)
        if buyer is None:
            return Response(
                {"error": {"code": "forbidden", "message": "You don't have write access to this buyer account."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = CheckoutSerializer(data=request.data, context={"request": request, "buyer": buyer})
        serializer.is_valid(raise_exception=True)
        order = serializer.create_order()
        notify_order_placed(order)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="update_status")
    def update_status(self, request, pk=None):
        order = self.get_object()
        serializer = OrderStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data["status"]
        # transition_status raises ValidationError on invalid moves
        order.transition_status(new_status, changed_by=request.user)

        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=["post"], url_path="assign_driver")
    def assign_driver(self, request, pk=None):
        """Admin-only. Assigns an approved driver to a ready_for_pickup order."""
        if request.user.role != "admin":
            return Response(
                {"error": {"code": "forbidden", "message": "Only admins can assign drivers."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        order = self.get_object()
        serializer = DriverAssignSerializer(
            data=request.data, context={"order": order}
        )
        serializer.is_valid(raise_exception=True)

        order.driver = serializer._driver
        order.save(update_fields=["driver"])
        notify_driver_assigned(order)

        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=["post"], url_path="reorder")
    def reorder(self, request, pk=None):
        """
        Populates the buyer's active cart with the products/quantities from this
        past order, at today's prices. Products that are no longer available are
        skipped (not failed) and listed in the response.
        """
        if request.user.role != "customer":
            return Response(
                {"error": {"code": "forbidden", "message": "Only customers can reorder."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        order = self.get_object()
        buyer = resolve_active_buyer_profile(request, require_write=True)
        if buyer is None:
            return Response(
                {"error": {"code": "forbidden", "message": "You don't have write access to this buyer account."}},
                status=status.HTTP_403_FORBIDDEN,
            )

        cart, _ = Cart.objects.get_or_create(buyer=buyer, status=CartStatus.ACTIVE)

        added = []
        skipped = []

        for item in order.items.select_related("product"):
            product = item.product

            if not product.is_available:
                skipped.append({
                    "product_id": product.id, "product_name": product.name,
                    "reason": "no longer available",
                })
                continue

            if product.stock_quantity <= 0:
                skipped.append({
                    "product_id": product.id, "product_name": product.name,
                    "reason": "out of stock",
                })
                continue

            quantity = min(item.quantity, product.stock_quantity)

            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={"quantity": quantity, "price_at_add": product.price},
            )
            if not created:
                cart_item.quantity = quantity
                cart_item.price_at_add = product.price
                cart_item.save(update_fields=["quantity", "price_at_add"])

            added.append({"product_id": product.id, "product_name": product.name, "quantity": quantity})

        return Response(
            {"cart": CartSerializer(cart).data, "added": added, "skipped": skipped},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="pickup_details")
    def pickup_details(self, request, pk=None):
        """Driver-only. Returns farm locations and contacts needed for pickup."""
        if request.user.role != "driver":
            return Response(
                {"error": {"code": "forbidden", "message": "Only drivers can view pickup details."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        order = self.get_object()
        # get_object() already filters queryset by driver FK for driver role,
        # so if we reach here the driver is already confirmed as the assignee.
        serializer = PickupDetailSerializer(order)
        return Response(serializer.data)


class InvoiceViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET   /api/v1/invoices/          — list (business buyer: own; admin: all, ?status=)
    GET   /api/v1/invoices/<id>/     — detail
    PATCH /api/v1/invoices/<id>/     — admin-only: update status
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Invoice.objects.select_related("buyer__user", "order")

        if user.role == "admin":
            status_param = self.request.query_params.get("status")
            if status_param:
                qs = qs.filter(status=status_param)
            return qs

        accessible_ids = [p.id for p in get_accessible_buyer_profiles(user)]
        return qs.filter(buyer_id__in=accessible_ids)

    def get_serializer_class(self):
        if self.action in ("update", "partial_update"):
            return InvoiceStatusUpdateSerializer
        return InvoiceSerializer

    def get_permissions(self):
        if self.action in ("update", "partial_update"):
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        invoice = serializer.save()
        return Response(InvoiceSerializer(invoice).data)
