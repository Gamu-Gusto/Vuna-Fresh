"""
Removing and restoring a farmer's product.

remove_product: a product that has been ordered is archived — hidden from the
shop, but kept so past orders, invoices, payouts and reviews stay intact. One
that was never ordered is deleted outright. Either way it leaves the shop at
once: it's taken out of buyers' carts, its surplus offers are withdrawn, and
recurring subscriptions to it are cancelled with the buyer notified.

restore_product: brings an archived product back to the farmer's list, hidden
from buyers until the farmer updates its stock and lists it again.
"""
from django.db import transaction
from django.utils import timezone

from apps.notifications.models import NotificationCategory
from apps.notifications.services.dispatcher import notify


class RestoreError(Exception):
    pass


def _end_dependents(product):
    """Take the product out of carts, surplus offers and subscriptions. Returns
    the subscriptions it cancelled, for notifying their buyers afterwards."""
    from apps.orders.models import CartItem, CartStatus
    from apps.subscriptions.models import Subscription, SubscriptionStatus

    from .models import SurplusListing, SurplusListingStatus

    CartItem.objects.filter(product=product, cart__status=CartStatus.ACTIVE).delete()
    SurplusListing.objects.filter(product=product, status=SurplusListingStatus.ACTIVE).update(
        status=SurplusListingStatus.WITHDRAWN,
    )
    cancelled = list(
        Subscription.objects.filter(product=product)
        .exclude(status=SubscriptionStatus.CANCELLED)
        .select_related("buyer__user")
    )
    Subscription.objects.filter(pk__in=[s.pk for s in cancelled]).update(status=SubscriptionStatus.CANCELLED)
    return cancelled


def remove_product(product):
    """Archive (if ever ordered) or delete. Returns "archived" or "deleted"."""
    from apps.orders.models import OrderItem

    name, farm = product.name, product.farmer.farm_name
    with transaction.atomic():
        cancelled = _end_dependents(product)
        if OrderItem.objects.filter(product=product).exists():
            product.is_archived = True
            product.archived_at = timezone.now()
            product.is_available = False
            product.save(update_fields=["is_archived", "archived_at", "is_available", "updated_at"])
            result = "archived"
        else:
            product.delete()
            result = "deleted"

    for subscription in cancelled:
        notify(
            subscription.buyer.user, "subscription_cancelled",
            f"Your subscription to {name} from {farm} has been cancelled because the farm "
            f"no longer sells it. You won't be charged for it again.",
            NotificationCategory.ORDER_UPDATES, link="/subscriptions",
        )
    return result


def restore_product(product):
    """Back to the farmer's list, still hidden from buyers until they list it."""
    if not product.is_archived:
        raise RestoreError("This product isn't archived.")
    if product.catalogue_item_id and not product.catalogue_item.is_active:
        raise RestoreError("This product is no longer in the catalogue, so it can't be restored.")
    product.is_archived = False
    product.archived_at = None
    product.save(update_fields=["is_archived", "archived_at", "updated_at"])
    return product
