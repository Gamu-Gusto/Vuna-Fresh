"""
Minimum order value, so every delivery covers its cost: R300 for household
buyers and R900 for businesses (settings MINIMUM_ORDER_HOUSEHOLD /
MINIMUM_ORDER_BUSINESS). Only the produce counts, not delivery. Applies at
checkout and to each delivery of a recurring subscription.
"""
from decimal import Decimal

from django.conf import settings


def minimum_for(buyer):
    business = getattr(buyer, "buyer_type", None) == "business"
    amount = settings.MINIMUM_ORDER_BUSINESS if business else settings.MINIMUM_ORDER_HOUSEHOLD
    return ("business" if business else "household"), Decimal(str(amount)).quantize(Decimal("0.01"))


def minimum_order_check(buyer, amount):
    """{"kind", "minimum", "shortfall", "message"} — shortfall is 0 when the minimum is met."""
    kind, minimum = minimum_for(buyer)
    shortfall = max(minimum - Decimal(amount), Decimal("0.00")).quantize(Decimal("0.01"))
    message = (
        f"The minimum {'business' if kind == 'business' else 'household'} order is R{minimum:.2f} "
        f"of produce. Add R{shortfall:.2f} more to check out."
        if shortfall > 0 else ""
    )
    return {"kind": kind, "minimum": minimum, "shortfall": shortfall, "message": message}
