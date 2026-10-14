from django.conf import settings
from django.db import models


class BusinessType(models.TextChoices):
    RETAILER = "retailer", "Retailer"
    RESTAURANT = "restaurant", "Restaurant"
    SPAZA_SHOP = "spaza_shop", "Spaza Shop"
    OTHER = "other", "Other"


class CreditTerms(models.TextChoices):
    PREPAID = "prepaid", "Prepaid"
    NET_7 = "net_7", "Net 7"
    NET_14 = "net_14", "Net 14"
    NET_30 = "net_30", "Net 30"


# Invoice due date = delivery date + N days. Prepaid orders aren't invoiced at
# all (see Order.transition_status), so there's no entry for it here.
CREDIT_TERM_DUE_DAYS = {
    CreditTerms.NET_7: 7,
    CreditTerms.NET_14: 14,
    CreditTerms.NET_30: 30,
}


class BusinessApprovalStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"


class BusinessBuyerDetails(models.Model):
    buyer = models.OneToOneField(
        "users.BuyerProfile",
        on_delete=models.CASCADE,
        related_name="business_details",
    )
    business_name = models.CharField(max_length=255)
    business_type = models.CharField(max_length=20, choices=BusinessType.choices)
    registration_number = models.CharField(max_length=100, null=True, blank=True)
    billing_address = models.ForeignKey(
        "users.Address",
        on_delete=models.PROTECT,
        related_name="+",
    )
    credit_terms = models.CharField(max_length=10, choices=CreditTerms.choices, default=CreditTerms.PREPAID)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    approval_status = models.CharField(
        max_length=10, choices=BusinessApprovalStatus.choices, default=BusinessApprovalStatus.PENDING
    )
    rejection_reason = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_business_buyers",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "business_buyer_details"
        verbose_name_plural = "business buyer details"

    def __str__(self):
        return f"BusinessBuyerDetails({self.business_name}, {self.approval_status})"


class BuyerAccountMemberRole(models.TextChoices):
    OWNER = "owner", "Owner"
    BUYER = "buyer", "Buyer"
    VIEWER = "viewer", "Viewer"


class BuyerAccountMember(models.Model):
    """
    Links a User to a business BuyerProfile so more than one person can act on
    one business account. NOTE: this is membership/authorization bookkeeping
    only — Cart/Order/checkout still resolve "the buyer" via
    request.user.buyer_profile everywhere else in the codebase, so only the
    account owner (whose own BuyerProfile this is) can actually place orders
    today. Letting other members transact against the shared account is a
    separate, larger follow-up (would touch IsBuyer/cart resolution across
    orders/reviews/subscriptions) — flagged, not built here.
    """
    buyer_profile = models.ForeignKey(
        "users.BuyerProfile",
        on_delete=models.CASCADE,
        related_name="account_members",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="buyer_account_memberships",
    )
    role = models.CharField(max_length=10, choices=BuyerAccountMemberRole.choices, default=BuyerAccountMemberRole.BUYER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "buyer_account_members"
        unique_together = [("buyer_profile", "user")]

    def __str__(self):
        return f"BuyerAccountMember({self.user.email}, {self.buyer_profile_id}, {self.role})"
