"""
Which commission rate applies to a sale. Vuna Fresh keeps the commission and
pays the farmer the rest (see payouts.py).

  - Discounted surplus produce: the surplus rate (default 5%), for any buyer,
    so surplus stays worth selling.
  - Business buyers: their account's own rate if one was agreed (5-8%),
    otherwise the business rate (default 8%).
  - Household buyers: the household rate (default 10%).

The rate is recorded on each order item when it's ordered (OrderItem.save),
so changing the rates later doesn't change what's owed on past orders.
"""
from decimal import Decimal

from ..models import CommissionSettings

DEFAULT_RATES = {
    "household": Decimal("10.00"),
    "business": Decimal("8.00"),
    "surplus": Decimal("5.00"),
}


def current_rates():
    settings = CommissionSettings.get_active()
    if settings is None:
        return dict(DEFAULT_RATES)
    return {
        "household": settings.commission_rate,
        "business": settings.business_rate,
        "surplus": settings.surplus_rate,
    }


def commission_rate_for(buyer, is_surplus=False):
    rates = current_rates()
    if is_surplus:
        return rates["surplus"]
    if getattr(buyer, "buyer_type", None) == "business":
        details = getattr(buyer, "business_details", None)
        if details is not None and details.commission_rate is not None:
            return details.commission_rate
        return rates["business"]
    return rates["household"]
