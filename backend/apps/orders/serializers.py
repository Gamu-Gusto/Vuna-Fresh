from decimal import Decimal
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import Cart, CartItem, Invoice, InvoiceStatus, Order, OrderItem, OrderStatus, OrderStatusHistory


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_unit = serializers.CharField(source="product.unit", read_only=True)
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ["id", "product", "product_name", "product_unit", "quantity", "price_at_add", "line_total"]
        read_only_fields = ["id", "price_at_add"]

    def get_line_total(self, obj):
        return obj.price_at_add * obj.quantity


class CartItemAddSerializer(serializers.Serializer):
    """
    Used for POST /cart/add_item/ — validates input before touching CartItem.

    An optional surplus_listing_id buys at that listing's discounted price
    instead of the product's regular price (capped by the listing's own
    quantity_available, not the product's general stock_quantity) — same
    price-snapshotting principle as a regular add, just a different source
    price. self._unit_price is what the view uses for CartItem.price_at_add.
    """
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    surplus_listing_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_product_id(self, value):
        from apps.products.models import Product
        try:
            product = Product.objects.get(pk=value, is_available=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found or unavailable.")
        self._product = product
        return value

    def validate(self, attrs):
        from django.utils import timezone

        from apps.products.models import SurplusListing, SurplusListingStatus

        product = getattr(self, "_product", None)
        quantity = attrs["quantity"]
        surplus_listing_id = attrs.get("surplus_listing_id")

        self._unit_price = product.price if product else None

        if surplus_listing_id is not None:
            try:
                listing = SurplusListing.objects.get(
                    pk=surplus_listing_id, product=product, status=SurplusListingStatus.ACTIVE,
                )
            except SurplusListing.DoesNotExist:
                raise serializers.ValidationError(
                    {"surplus_listing_id": "Surplus listing not found or no longer active."}
                )
            if listing.expires_at <= timezone.now():
                raise serializers.ValidationError({"surplus_listing_id": "This surplus listing has expired."})
            if quantity > listing.quantity_available:
                raise serializers.ValidationError(
                    {"quantity": f"Only {listing.quantity_available} units available at surplus price."}
                )
            self._unit_price = listing.effective_price
        elif product and quantity > product.stock_quantity:
            raise serializers.ValidationError(
                {"quantity": f"Only {product.stock_quantity} units available."}
            )

        return attrs


class CartItemUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ["quantity"]

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        product = self.instance.product
        if value > product.stock_quantity:
            raise serializers.ValidationError(f"Only {product.stock_quantity} units available.")
        return value


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    cart_total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "status", "items", "cart_total", "created_at", "updated_at"]

    def get_cart_total(self, obj):
        return sum(item.price_at_add * item.quantity for item in obj.items.all())


# ── Order serializers ─────────────────────────────────────────────────────────

class OrderStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_email = serializers.EmailField(source="changed_by.email", read_only=True)

    class Meta:
        model = OrderStatusHistory
        fields = ["id", "status", "changed_at", "changed_by_email"]


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_unit = serializers.CharField(source="product.unit", read_only=True)
    farm_name = serializers.CharField(source="farmer.farm_name", read_only=True)
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            "id", "product", "product_name", "product_unit",
            "farmer", "farm_name", "quantity", "price_at_purchase", "line_total",
        ]

    def get_line_total(self, obj):
        return obj.line_total


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    buyer_email = serializers.EmailField(source="buyer.user.email", read_only=True)
    payment = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "buyer_email",
            "delivery_address",
            "driver",
            "status",
            "scheduled_delivery_time",
            "subtotal",
            "delivery_fee",
            "total",
            "items",
            "status_history",
            "payment_terms",
            "payment",
            "created_at",
        ]
        read_only_fields = [
            "id", "buyer_email", "driver", "status",
            "subtotal", "delivery_fee", "total", "items", "status_history", "payment_terms", "payment",
            "created_at",
        ]

    def get_payment(self, obj):
        """
        Payment state for display: 'credit' (invoiced on delivery), 'paid',
        'proof_submitted', 'awaiting_payment' (EFT details issued, no proof yet,
        or proof rejected) or 'unpaid' (no payment started).
        """
        if obj.payment_terms in ("net_7", "net_14", "net_30"):
            return {"status": "credit"}

        payments = [t for t in obj.transactions.all() if t.type == "payment"]
        if any(t.status == "completed" for t in payments):
            return {"status": "paid"}

        open_txn = next((t for t in payments if t.status == "awaiting_verification"), None)
        if open_txn is None:
            return {"status": "unpaid"}

        proofs = list(open_txn.deposit_proofs.all())
        submitted = any(p.status == "pending_review" for p in proofs)
        return {
            "status": "proof_submitted" if submitted else "awaiting_payment",
            "transaction_id": open_txn.id,
            "reference": open_txn.provider_reference,
        }


class CheckoutSerializer(serializers.Serializer):
    """Input for POST /orders/ — creates an Order from the buyer's active cart."""
    delivery_address_id = serializers.IntegerField()
    scheduled_delivery_time = serializers.DateTimeField(required=False, allow_null=True)

    def validate_delivery_address_id(self, value):
        from apps.users.models import Address
        request = self.context["request"]
        buyer = self.context["buyer"]
        try:
            address = Address.objects.get(pk=value)
        except Address.DoesNotExist:
            raise serializers.ValidationError("Address not found or does not belong to you.")
        # Allowed if it's the acting member's own address, or the buyer
        # account's own address (e.g. the business's registered address).
        if address.user_id not in (request.user.id, buyer.user_id):
            raise serializers.ValidationError("Address not found or does not belong to you.")
        self._address = address
        return value

    def validate(self, attrs):
        buyer = self.context["buyer"]
        try:
            cart = Cart.objects.get(buyer=buyer, status="active")
        except Cart.DoesNotExist:
            raise serializers.ValidationError("You have no active cart.")
        if not cart.items.exists():
            raise serializers.ValidationError("Your cart is empty.")
        self._cart = cart
        return attrs

    def create_order(self):
        from decimal import Decimal
        request = self.context["request"]
        cart = self._cart
        address = self._address
        buyer = self.context["buyer"]

        subtotal = Decimal("0.00")
        order_items_data = []

        for cart_item in cart.items.select_related("product__farmer"):
            subtotal += cart_item.price_at_add * cart_item.quantity
            order_items_data.append({
                "product": cart_item.product,
                "farmer": cart_item.product.farmer,
                "quantity": cart_item.quantity,
                "price_at_purchase": cart_item.price_at_add,
            })

        delivery_fee = Decimal("0.00")
        total = subtotal + delivery_fee

        # Business buyers: flag as bulk and snapshot their current credit terms.
        # Non-prepaid business orders get invoiced on delivery instead of paid at
        # checkout (see Order.transition_status) — prepaid business orders behave
        # exactly like individual checkout for now; no payment flow exists yet to
        # wire prepaid into either way.
        is_bulk = False
        payment_terms = None
        business_details = getattr(buyer, "business_details", None)
        if buyer.buyer_type == "business" and business_details is not None:
            is_bulk = True
            payment_terms = business_details.credit_terms

        order = Order.objects.create(
            buyer=buyer,
            delivery_address=address,
            status=OrderStatus.PLACED,
            scheduled_delivery_time=self.validated_data.get("scheduled_delivery_time"),
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total=total,
            is_bulk=is_bulk,
            payment_terms=payment_terms,
        )

        for item_data in order_items_data:
            OrderItem.objects.create(order=order, **item_data)

        # Log initial status
        OrderStatusHistory.objects.create(
            order=order,
            status=OrderStatus.PLACED,
            changed_by=request.user,
        )

        # Mark cart as converted
        cart.status = "converted"
        cart.save(update_fields=["status"])

        return order


class OrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=OrderStatus.choices)


class DriverAssignSerializer(serializers.Serializer):
    """Admin-only. Assigns a driver to an order that is in 'ready_for_pickup' status."""
    driver_id = serializers.IntegerField()

    def validate_driver_id(self, value):
        from apps.users.models import DriverProfile
        try:
            driver = DriverProfile.objects.select_related("user").get(pk=value, is_approved=True)
        except DriverProfile.DoesNotExist:
            raise serializers.ValidationError("Driver not found or not yet approved.")
        self._driver = driver
        return value

    def validate(self, attrs):
        order = self.context["order"]
        if order.status != OrderStatus.READY_FOR_PICKUP:
            raise serializers.ValidationError(
                f"A driver can only be assigned to an order in 'ready_for_pickup' status "
                f"(current status: '{order.status}')."
            )
        return attrs


class PickupItemDetailSerializer(serializers.Serializer):
    """Per-item pickup info: what to collect and from which farm."""
    order_item_id = serializers.IntegerField(source="id")
    product_name = serializers.CharField(source="product.name")
    quantity = serializers.IntegerField()
    unit = serializers.CharField(source="product.unit")
    farm_name = serializers.CharField(source="farmer.farm_name")
    farm_location = serializers.CharField(source="farmer.farm_location")
    farmer_email = serializers.EmailField(source="farmer.user.email")
    farmer_phone = serializers.CharField(source="farmer.user.phone")


class PickupDetailSerializer(serializers.Serializer):
    """Full pickup details for a driver's assigned order."""
    order_id = serializers.IntegerField(source="id")
    status = serializers.CharField()
    scheduled_delivery_time = serializers.DateTimeField()
    items = serializers.SerializerMethodField()
    delivery_address = serializers.SerializerMethodField()

    def get_items(self, obj):
        items = obj.items.select_related("product", "farmer__user")
        return PickupItemDetailSerializer(items, many=True).data

    def get_delivery_address(self, obj):
        addr = obj.delivery_address
        return {
            "street_address": addr.street_address,
            "suburb": addr.suburb,
            "city": addr.city,
            "province": addr.province,
            "postal_code": addr.postal_code,
        }


# ── Invoice serializers ───────────────────────────────────────────────────────

class InvoiceSerializer(serializers.ModelSerializer):
    buyer_email = serializers.EmailField(source="buyer.user.email", read_only=True)

    class Meta:
        model = Invoice
        fields = ["id", "buyer", "buyer_email", "order", "amount", "due_date", "status", "issued_at", "paid_at"]
        read_only_fields = fields


class InvoiceStatusUpdateSerializer(serializers.ModelSerializer):
    """Admin-only — moves an invoice between pending/paid/overdue/written_off."""

    class Meta:
        model = Invoice
        fields = ["status"]

    def update(self, instance, validated_data):
        new_status = validated_data.get("status", instance.status)
        instance.status = new_status
        if new_status == InvoiceStatus.PAID:
            if instance.paid_at is None:
                from django.utils import timezone
                instance.paid_at = timezone.now()
        else:
            instance.paid_at = None
        instance.save(update_fields=["status", "paid_at"])
        return instance
