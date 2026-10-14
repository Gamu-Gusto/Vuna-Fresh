from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.orders.models import Order, OrderItem, OrderStatus, OrderStatusHistory
from apps.subscriptions.models import Subscription, SubscriptionStatus

# NOTE: this command is not wired to a scheduler yet. In production it needs to run
# on a recurring schedule (Celery beat task or cron job calling `manage.py
# process_subscriptions`) — that wiring is out of scope for now. For now, run it
# manually: `python manage.py process_subscriptions`.


class Command(BaseCommand):
    help = "Creates orders for subscriptions whose next_delivery_date has passed, and advances their schedule."

    def handle(self, *args, **options):
        due = Subscription.objects.filter(
            status=SubscriptionStatus.ACTIVE,
            next_delivery_date__lte=date.today(),
        ).select_related("buyer__user", "buyer__preferred_delivery_address", "product")

        created_count = 0
        skipped_count = 0

        for subscription in due:
            address = subscription.buyer.preferred_delivery_address
            if address is None:
                address = subscription.buyer.user.addresses.filter(is_default=True).first()
            if address is None:
                self.stdout.write(self.style.WARNING(
                    f"Skipping subscription {subscription.id}: buyer has no delivery address set."
                ))
                skipped_count += 1
                continue

            product = subscription.product
            if not product.is_available or product.stock_quantity < subscription.quantity:
                self.stdout.write(self.style.WARNING(
                    f"Skipping subscription {subscription.id}: '{product.name}' is unavailable or out of stock."
                ))
                skipped_count += 1
                continue

            with transaction.atomic():
                price = product.price
                subtotal = price * subscription.quantity
                order = Order.objects.create(
                    buyer=subscription.buyer,
                    delivery_address=address,
                    status=OrderStatus.PLACED,
                    subtotal=subtotal,
                    delivery_fee=Decimal("0.00"),
                    total=subtotal,
                )
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    farmer=product.farmer,
                    quantity=subscription.quantity,
                    price_at_purchase=price,
                )
                OrderStatusHistory.objects.create(
                    order=order,
                    status=OrderStatus.PLACED,
                    changed_by=subscription.buyer.user,
                )
                subscription.advance_next_delivery_date()

            created_count += 1
            self.stdout.write(self.style.SUCCESS(
                f"Created order {order.id} for subscription {subscription.id} ({product.name})."
            ))

        self.stdout.write(self.style.SUCCESS(
            f"Done. {created_count} order(s) created, {skipped_count} subscription(s) skipped."
        ))
