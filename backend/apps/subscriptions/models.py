from datetime import timedelta

from django.db import models


class SubscriptionFrequency(models.TextChoices):
    WEEKLY = "weekly", "Weekly"
    BIWEEKLY = "biweekly", "Biweekly"
    MONTHLY = "monthly", "Monthly"


# Approximated in fixed days since we don't have dateutil for calendar-accurate
# month arithmetic. Close enough for a delivery schedule.
FREQUENCY_DAYS = {
    SubscriptionFrequency.WEEKLY: 7,
    SubscriptionFrequency.BIWEEKLY: 14,
    SubscriptionFrequency.MONTHLY: 30,
}


class SubscriptionStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    CANCELLED = "cancelled", "Cancelled"


class Subscription(models.Model):
    buyer = models.ForeignKey(
        "users.BuyerProfile",
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    quantity = models.PositiveIntegerField(default=1)
    frequency = models.CharField(max_length=10, choices=SubscriptionFrequency.choices)
    next_delivery_date = models.DateField()
    status = models.CharField(max_length=10, choices=SubscriptionStatus.choices, default=SubscriptionStatus.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "subscriptions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Subscription({self.buyer.user.email}, {self.product.name}, {self.frequency})"

    def advance_next_delivery_date(self):
        self.next_delivery_date = self.next_delivery_date + timedelta(days=FREQUENCY_DAYS[self.frequency])
        self.save(update_fields=["next_delivery_date"])
