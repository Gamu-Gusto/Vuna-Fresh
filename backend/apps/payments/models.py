from django.conf import settings
from django.db import models


class PaymentMethodType(models.TextChoices):
    CARD = "card", "Card"
    MOBILE_WALLET = "mobile_wallet", "Mobile Wallet"
    BANK_ACCOUNT = "bank_account", "Bank Account"


class PaymentProviderChoice(models.TextChoices):
    PAYFAST = "payfast", "PayFast"
    PAYSTACK = "paystack", "PayStack"
    DIRECT_DEPOSIT = "direct_deposit", "Direct Deposit"


class PaymentMethod(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_methods",
    )
    type = models.CharField(max_length=20, choices=PaymentMethodType.choices)
    provider = models.CharField(max_length=20, choices=PaymentProviderChoice.choices)
    provider_token = models.CharField(
        max_length=255,
        help_text="Opaque token/reference from the provider — never a raw card number.",
    )
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "payment_methods"
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"PaymentMethod({self.user.email}, {self.provider}, {self.type})"

    def save(self, *args, **kwargs):
        # Enforce only one default payment method per user (same pattern as users.Address).
        if self.is_default:
            PaymentMethod.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(
                is_default=False
            )
        super().save(*args, **kwargs)


class TransactionProvider(models.TextChoices):
    PAYFAST = "payfast", "PayFast"
    PAYSTACK = "paystack", "PayStack"
    DIRECT_DEPOSIT = "direct_deposit", "Direct Deposit"
    INTERNAL = "internal", "Internal"


class TransactionType(models.TextChoices):
    PAYMENT = "payment", "Payment"
    REFUND = "refund", "Refund"
    FARMER_PAYOUT = "farmer_payout", "Farmer Payout"


class TransactionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    AWAITING_VERIFICATION = "awaiting_verification", "Awaiting Verification"


class Transaction(models.Model):
    """
    A buyer PAYMENT transaction and a farmer_payout transaction are always two
    separate rows — one is the buyer paying Vuna Fresh, the other is Vuna Fresh
    paying the farmer their share afterward. Never combine them.
    """
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    provider = models.CharField(max_length=20, choices=TransactionProvider.choices)
    type = models.CharField(max_length=20, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=25, choices=TransactionStatus.choices, default=TransactionStatus.PENDING)
    provider_reference = models.CharField(
        max_length=255, null=True, blank=True,
        help_text="External transaction ID (PayFast pf_payment_id, etc.) or the buyer's bank "
                   "deposit reference — used for reconciliation.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "transactions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Transaction({self.pk}, {self.type}, {self.provider}, {self.status}, R{self.amount})"


class DirectDepositProofStatus(models.TextChoices):
    PENDING_REVIEW = "pending_review", "Pending Review"
    VERIFIED = "verified", "Verified"  # funds confirmed cleared in the bank account
    REJECTED = "rejected", "Rejected"


class DirectDepositProof(models.Model):
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="deposit_proofs",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="uploaded_deposit_proofs",
    )
    file_url = models.URLField()
    bank_reference_number = models.CharField(
        max_length=100,
        help_text="The reference the buyer was told to use, so it can be matched to their bank statement.",
    )
    status = models.CharField(
        max_length=20, choices=DirectDepositProofStatus.choices, default=DirectDepositProofStatus.PENDING_REVIEW
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_deposit_proofs",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    # What the reviewing admin saw on Vuna Fresh's own bank statement when they
    # confirmed the funds had cleared. An uploaded proof alone is never enough
    # to mark an order paid (a proof can be forged, or the payment reversed).
    amount_received = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    received_on = models.DateField(null=True, blank=True)
    bank_statement_reference = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "direct_deposit_proofs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"DirectDepositProof(transaction={self.transaction_id}, {self.status})"


class CommissionSettings(models.Model):
    """
    One active commission rate at a time (not per-farmer/per-category). Rows
    are append-only and effective-dated rather than a strict single row, so a
    rate change is auditable — get_active() always resolves to exactly one.
    """
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, help_text="Percentage, e.g. 10.00 for 10%.",
    )
    effective_from = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "commission_settings"
        ordering = ["-effective_from"]

    def __str__(self):
        return f"CommissionSettings({self.commission_rate}%, from {self.effective_from})"

    @classmethod
    def get_active(cls):
        from django.utils import timezone
        return cls.objects.filter(effective_from__lte=timezone.now()).order_by("-effective_from").first()


class FarmerPayoutStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PAID = "paid", "Paid"


class FarmerPayout(models.Model):
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="farmer_payouts",
    )
    farmer = models.ForeignKey(
        "users.FarmerProfile",
        on_delete=models.PROTECT,
        related_name="payouts",
    )
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Farmer's share before commission.")
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="What actually gets paid out.")
    status = models.CharField(max_length=10, choices=FarmerPayoutStatus.choices, default=FarmerPayoutStatus.PENDING)
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="farmer_payout_records",
        help_text="The farmer_payout Transaction, created once this payout is marked paid.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "farmer_payouts"
        ordering = ["-created_at"]
        unique_together = [("order", "farmer")]

    def __str__(self):
        return f"FarmerPayout(order={self.order_id}, farmer={self.farmer_id}, {self.status})"
