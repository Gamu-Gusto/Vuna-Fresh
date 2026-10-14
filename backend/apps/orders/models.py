from django.conf import settings
from django.db import models
from rest_framework.exceptions import ValidationError

from apps.buyers.models import CREDIT_TERM_DUE_DAYS, CreditTerms


class CartStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    SAVED = "saved", "Saved"
    EXPIRED = "expired", "Expired"
    CONVERTED = "converted", "Converted"


class OrderStatus(models.TextChoices):
    PLACED = "placed", "Placed"
    PREPARING = "preparing", "Preparing"
    READY_FOR_PICKUP = "ready_for_pickup", "Ready for Pickup"
    OUT_FOR_DELIVERY = "out_for_delivery", "Out for Delivery"
    DELIVERED = "delivered", "Delivered"
    CANCELLED = "cancelled", "Cancelled"


# Allowed transitions per status: maps current status → set of valid next statuses
VALID_TRANSITIONS = {
    OrderStatus.PLACED: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.READY_FOR_PICKUP, OrderStatus.CANCELLED},
    OrderStatus.READY_FOR_PICKUP: {OrderStatus.OUT_FOR_DELIVERY, OrderStatus.CANCELLED},
    OrderStatus.OUT_FOR_DELIVERY: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}

# Which roles may trigger each target status
STATUS_ROLE_PERMISSIONS = {
    OrderStatus.PREPARING: {"farmer", "admin"},
    OrderStatus.READY_FOR_PICKUP: {"farmer", "admin"},
    OrderStatus.OUT_FOR_DELIVERY: {"driver", "admin"},
    OrderStatus.DELIVERED: {"driver", "admin"},
    OrderStatus.CANCELLED: {"admin"},
}


class Cart(models.Model):
    buyer = models.ForeignKey(
        "users.BuyerProfile",
        on_delete=models.CASCADE,
        related_name="carts",
    )
    status = models.CharField(max_length=10, choices=CartStatus.choices, default=CartStatus.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "carts"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Cart({self.buyer.user.email}, {self.status})"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="+")
    quantity = models.PositiveIntegerField(default=1)
    price_at_add = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "cart_items"
        unique_together = [("cart", "product")]

    def __str__(self):
        return f"CartItem({self.product.name} x{self.quantity})"


class OrderQuerySet(models.QuerySet):
    def released(self):
        """
        Orders farmers may see and prepare: credit-terms orders (invoiced on
        delivery), or prepaid orders whose payment has been confirmed. An EFT
        order is never released on an uploaded proof alone: its payment only
        completes once an admin confirms the funds cleared.
        """
        return self.filter(
            models.Q(payment_terms__in=CREDIT_TERM_DUE_DAYS)
            | models.Q(transactions__type="payment", transactions__status="completed")
        ).distinct()


class Order(models.Model):
    buyer = models.ForeignKey(
        "users.BuyerProfile",
        on_delete=models.PROTECT,
        related_name="orders",
    )
    delivery_address = models.ForeignKey(
        "users.Address",
        on_delete=models.PROTECT,
        related_name="orders",
    )
    driver = models.ForeignKey(
        "users.DriverProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PLACED)
    scheduled_delivery_time = models.DateTimeField(null=True, blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    is_bulk = models.BooleanField(default=False)
    payment_terms = models.CharField(
        max_length=10, choices=CreditTerms.choices, null=True, blank=True,
        help_text="Snapshot of the business buyer's credit_terms at order time, if any.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = OrderQuerySet.as_manager()

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order({self.pk}, {self.buyer.user.email}, {self.status})"

    @property
    def is_released(self):
        """See OrderQuerySet.released."""
        return self.payment_terms in CREDIT_TERM_DUE_DAYS or self.transactions.filter(
            type="payment", status="completed"
        ).exists()

    def transition_status(self, new_status, changed_by):
        """
        Move the order to new_status, validate the transition, and log history.
        Raises ValidationError if the transition is not allowed.
        Always call this instead of setting order.status directly.
        """
        current = self.status

        if new_status not in VALID_TRANSITIONS.get(current, set()):
            raise ValidationError(
                f"Cannot transition from '{current}' to '{new_status}'."
            )

        if new_status == OrderStatus.PREPARING and not self.is_released:
            raise ValidationError(
                "This order can't be prepared until its payment has been confirmed as received."
            )

        allowed_roles = STATUS_ROLE_PERMISSIONS.get(new_status, set())
        if changed_by.role not in allowed_roles:
            raise ValidationError(
                f"Your role ('{changed_by.role}') cannot set status to '{new_status}'."
            )

        # Driver can only move their own assigned order to out_for_delivery/delivered
        if changed_by.role == "driver" and new_status in (
            OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED
        ):
            try:
                if self.driver != changed_by.driver_profile:
                    raise ValidationError("You are not the assigned driver for this order.")
            except AttributeError:
                raise ValidationError("You are not the assigned driver for this order.")

        # Farmer can only move orders that contain at least one of their products
        if changed_by.role == "farmer" and new_status in (
            OrderStatus.PREPARING, OrderStatus.READY_FOR_PICKUP
        ):
            try:
                has_item = self.items.filter(farmer=changed_by.farmer_profile).exists()
            except AttributeError:
                has_item = False
            if not has_item:
                raise ValidationError("This order contains none of your products.")

        self.status = new_status
        self.save(update_fields=["status"])

        OrderStatusHistory.objects.create(
            order=self,
            status=new_status,
            changed_by=changed_by,
        )

        from .notifications import notify_status_changed
        notify_status_changed(self)

        # Business orders on credit terms (anything but prepaid) get invoiced on
        # delivery rather than requiring payment at checkout. Prepaid business
        # orders and individual-buyer orders are untouched here.
        if new_status == OrderStatus.DELIVERED and self.is_bulk and self.payment_terms in (
            CreditTerms.NET_7, CreditTerms.NET_14, CreditTerms.NET_30
        ):
            from datetime import timedelta

            from django.utils import timezone

            from apps.buyers.models import CREDIT_TERM_DUE_DAYS

            Invoice.objects.create(
                buyer=self.buyer,
                order=self,
                amount=self.total,
                due_date=timezone.now().date() + timedelta(days=CREDIT_TERM_DUE_DAYS[self.payment_terms]),
                status=InvoiceStatus.PENDING,
            )


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="+")
    farmer = models.ForeignKey(
        "users.FarmerProfile",
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    quantity = models.PositiveIntegerField()
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "order_items"

    def __str__(self):
        return f"OrderItem({self.product.name} x{self.quantity})"

    @property
    def line_total(self):
        return self.price_at_purchase * self.quantity


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    status = models.CharField(max_length=20, choices=OrderStatus.choices)
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="order_status_changes",
    )

    class Meta:
        db_table = "order_status_history"
        ordering = ["changed_at"]

    def __str__(self):
        return f"OrderStatusHistory(order={self.order_id}, {self.status})"


class InvoiceStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PAID = "paid", "Paid"
    OVERDUE = "overdue", "Overdue"
    WRITTEN_OFF = "written_off", "Written Off"


class Invoice(models.Model):
    buyer = models.ForeignKey(
        "users.BuyerProfile",
        on_delete=models.PROTECT,
        related_name="invoices",
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField()
    status = models.CharField(max_length=15, choices=InvoiceStatus.choices, default=InvoiceStatus.PENDING)
    issued_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "invoices"
        ordering = ["-issued_at"]

    def __str__(self):
        return f"Invoice({self.pk}, {self.buyer.user.email}, {self.status})"
