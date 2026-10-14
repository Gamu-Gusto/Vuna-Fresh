"""Order-related notifications (in-app + email via notifications.notify)."""
from apps.notifications.models import NotificationCategory
from apps.notifications.services.dispatcher import notify

from .models import OrderStatus

BUYER_STATUS_MESSAGES = {
    OrderStatus.PREPARING: "Your order #{id} is being prepared by the farm.",
    OrderStatus.READY_FOR_PICKUP: "Your order #{id} is packed and waiting for a driver.",
    OrderStatus.OUT_FOR_DELIVERY: "Your order #{id} is out for delivery.",
    OrderStatus.DELIVERED: "Your order #{id} has been delivered. Enjoy!",
    OrderStatus.CANCELLED: "Your order #{id} has been cancelled. Contact support if you have questions.",
}


def _farmer_users(order):
    return {item.farmer.user for item in order.items.select_related("farmer__user")}


def notify_order_placed(order):
    on_credit = order.payment_terms in ("net_7", "net_14", "net_30")
    if on_credit:
        notify(
            order.buyer.user, "order_placed",
            f"Order #{order.id} placed. It will be invoiced to your account on delivery.",
            NotificationCategory.ORDER_UPDATES, link="/orders",
        )
    else:
        notify(
            order.buyer.user, "order_placed",
            f"Order #{order.id} placed. Please pay R{order.total} by EFT and upload your proof of payment.",
            NotificationCategory.ORDER_UPDATES, link=f"/orders/{order.id}/pay",
        )

    # A prepaid order reaches farmers only once its payment is confirmed
    # (notify_order_paid); a credit order is released straight away.
    if on_credit:
        for farmer in _farmer_users(order):
            notify(
                farmer, "new_order",
                f"New order #{order.id} includes your products. You can start preparing it.",
                NotificationCategory.ORDER_UPDATES, link=f"/farmer/orders/{order.id}",
            )


def notify_order_paid(order):
    for farmer in _farmer_users(order):
        notify(
            farmer, "order_paid",
            f"New paid order #{order.id} includes your products. You can start preparing it.",
            NotificationCategory.ORDER_UPDATES, link=f"/farmer/orders/{order.id}",
        )


def notify_status_changed(order):
    template = BUYER_STATUS_MESSAGES.get(order.status)
    if template:
        notify(
            order.buyer.user, "order_status_changed", template.format(id=order.id),
            NotificationCategory.ORDER_UPDATES, link="/orders",
        )


def notify_driver_assigned(order):
    notify(
        order.driver.user, "delivery_assigned",
        f"You've been assigned delivery for order #{order.id}.",
        NotificationCategory.ORDER_UPDATES, link=f"/driver/deliveries/{order.id}",
    )
