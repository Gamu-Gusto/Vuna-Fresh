"""
Splits a completed buyer payment across the farmers represented in the
order, takes Vuna Fresh's commission off each item at the rate recorded when
it was ordered (see commission.py), and records one pending FarmerPayout per
farmer for the rest. Does NOT create the farmer_payout Transaction or
move any money — actually paying a farmer is a separate, manual admin action
(see views.FarmerPayoutViewSet.mark_paid), since there's no payout gateway
integration in scope yet.
"""
from decimal import ROUND_HALF_UP, Decimal

from ..models import FarmerPayout, FarmerPayoutStatus
from .commission import commission_rate_for


def calculate_and_create_payouts(transaction):
    """
    Given a completed buyer-payment Transaction for an Order, returns the
    list of FarmerPayout rows for that order (creating them on first call).
    Safe to call more than once for the same order — idempotent, returns the
    existing rows instead of duplicating them.
    """
    order = transaction.order
    if order is None:
        return []

    existing = list(FarmerPayout.objects.filter(order=order))
    if existing:
        return existing

    farmer_totals = {}
    for item in order.items.select_related("farmer"):
        entry = farmer_totals.setdefault(
            item.farmer_id, {"farmer": item.farmer, "gross": Decimal("0.00"), "commission": Decimal("0.00")},
        )
        line = item.price_at_purchase * item.quantity
        rate = item.commission_rate
        if rate is None:  # ordered before rates were recorded per item
            rate = commission_rate_for(order.buyer, is_surplus=item.surplus_listing_id is not None)
        entry["gross"] += line
        entry["commission"] += line * rate / Decimal("100")

    payouts = []
    for entry in farmer_totals.values():
        gross_amount = entry["gross"]
        commission_amount = entry["commission"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        net_amount = gross_amount - commission_amount
        payout, _created = FarmerPayout.objects.get_or_create(
            order=order,
            farmer=entry["farmer"],
            defaults={
                "gross_amount": gross_amount,
                "commission_amount": commission_amount,
                "net_amount": net_amount,
                "status": FarmerPayoutStatus.PENDING,
            },
        )
        payouts.append(payout)

    return payouts
