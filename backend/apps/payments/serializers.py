from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from apps.orders.models import OrderStatus
from apps.buyers.models import CreditTerms

from .models import (
    CommissionSettings,
    DirectDepositProof,
    DirectDepositProofStatus,
    FarmerPayout,
    FarmerPayoutStatus,
    PaymentMethod,
    Transaction,
    TransactionStatus,
    TransactionType,
)

# Business orders on these terms are invoiced on delivery (see orders.Order.transition_status),
# so there is nothing to pay at checkout.
CREDIT_PAYMENT_TERMS = (CreditTerms.NET_7, CreditTerms.NET_14, CreditTerms.NET_30)


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ["id", "type", "provider", "provider_token", "is_default", "created_at"]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ["id", "order", "user", "provider", "type", "amount", "status", "provider_reference", "created_at"]
        read_only_fields = fields


class InitiatePaymentSerializer(serializers.Serializer):
    """Input for POST /payments/initiate/ — order must already exist (created via
    the existing /orders/ checkout endpoint, untouched by this app)."""
    order_id = serializers.IntegerField()
    provider = serializers.ChoiceField(choices=["payfast", "direct_deposit"])

    def validate_order_id(self, value):
        from apps.buyers.resolvers import user_can_act_for_buyer_profile
        from apps.orders.models import Order

        request = self.context["request"]
        try:
            order = Order.objects.select_related("buyer").get(pk=value)
        except Order.DoesNotExist:
            raise serializers.ValidationError("Order not found.")

        if not user_can_act_for_buyer_profile(request.user, order.buyer, require_write=True):
            raise serializers.ValidationError("This order does not belong to you.")
        if order.status == OrderStatus.CANCELLED:
            raise serializers.ValidationError("This order has been cancelled.")
        if order.payment_terms in CREDIT_PAYMENT_TERMS:
            raise serializers.ValidationError("This order is on credit terms and will be invoiced on delivery.")
        if order.transactions.filter(type=TransactionType.PAYMENT, status=TransactionStatus.COMPLETED).exists():
            raise serializers.ValidationError("This order has already been paid.")

        self._order = order
        return value

    def validate_provider(self, value):
        if value == "payfast" and not settings.PAYFAST_ENABLED:
            raise serializers.ValidationError("Card payments are not available yet. Please pay by EFT.")
        return value


class DirectDepositProofSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(source="transaction.order_id", read_only=True)
    amount = serializers.DecimalField(source="transaction.amount", max_digits=12, decimal_places=2, read_only=True)
    expected_reference = serializers.CharField(source="transaction.provider_reference", read_only=True)
    uploaded_by_email = serializers.EmailField(source="uploaded_by.email", read_only=True)

    class Meta:
        model = DirectDepositProof
        fields = [
            "id", "transaction", "order_id", "amount", "expected_reference", "uploaded_by_email",
            "file_url", "bank_reference_number",
            "status", "reviewed_by", "reviewed_at", "notes",
            "amount_received", "received_on", "bank_statement_reference", "created_at",
        ]
        read_only_fields = [
            "id", "status", "reviewed_by", "reviewed_at",
            "amount_received", "received_on", "bank_statement_reference", "created_at",
        ]

    def validate_transaction(self, value):
        request = self.context["request"]
        if value.user_id != request.user.id:
            raise serializers.ValidationError("This transaction does not belong to you.")
        if value.provider != "direct_deposit":
            raise serializers.ValidationError("This transaction is not a direct deposit payment.")
        if value.status != "awaiting_verification":
            raise serializers.ValidationError("This transaction is not awaiting verification.")
        if value.deposit_proofs.filter(status=DirectDepositProofStatus.PENDING_REVIEW).exists():
            raise serializers.ValidationError("Proof for this payment is already waiting for review.")
        return value

    def create(self, validated_data):
        validated_data["uploaded_by"] = self.context["request"].user
        return super().create(validated_data)


class DirectDepositReviewSerializer(serializers.Serializer):
    """
    Approving means the admin has seen the money arrive in Vuna Fresh's bank
    account, not just the buyer's proof. They record what the bank statement
    shows, and it must cover the amount due. context["proof"] is the proof.
    """
    action = serializers.ChoiceField(choices=["approve", "reject"])
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    funds_cleared = serializers.BooleanField(required=False, default=False)
    amount_received = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    received_on = serializers.DateField(required=False)
    bank_statement_reference = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs["action"] == "reject":
            if not attrs.get("notes", "").strip():
                raise serializers.ValidationError({"notes": "A reason is required when rejecting."})
            return attrs

        errors = {}
        if not attrs["funds_cleared"]:
            errors["funds_cleared"] = (
                "Confirm you have checked the Vuna Fresh bank account and the funds have cleared. "
                "An uploaded proof of payment is not enough."
            )
        if attrs.get("amount_received") is None:
            errors["amount_received"] = "Enter the amount shown on the bank statement."
        if attrs.get("received_on") is None:
            errors["received_on"] = "Enter the date the funds arrived, from the bank statement."
        elif attrs["received_on"] > timezone.localdate():
            errors["received_on"] = "The date funds arrived can't be in the future."
        attrs["bank_statement_reference"] = attrs["bank_statement_reference"].strip()
        if not attrs["bank_statement_reference"]:
            errors["bank_statement_reference"] = "Enter the reference shown on the bank statement."
        if errors:
            raise serializers.ValidationError(errors)

        proof = self.context["proof"]
        due = proof.transaction.amount
        if attrs["amount_received"] < due:
            raise serializers.ValidationError({"amount_received": (
                f"R{attrs['amount_received']} received is less than the R{due} due. Don't approve a "
                f"short payment: reject it with a reason, or wait for the balance to clear."
            )})

        # The same bank deposit can't pay for two orders (e.g. one proof uploaded twice)
        reused = DirectDepositProof.objects.filter(
            status=DirectDepositProofStatus.VERIFIED,
            bank_statement_reference__iexact=attrs["bank_statement_reference"],
            received_on=attrs["received_on"],
            amount_received=attrs["amount_received"],
        ).exclude(pk=proof.pk).select_related("transaction").first()
        if reused:
            raise serializers.ValidationError({"bank_statement_reference": (
                f"This deposit (same reference, date and amount) already paid for order "
                f"#{reused.transaction.order_id}. Check the bank statement for a separate deposit."
            )})
        return attrs


class FarmerPayoutSerializer(serializers.ModelSerializer):
    farm_name = serializers.CharField(source="farmer.farm_name", read_only=True)
    order_id = serializers.IntegerField(source="order.id", read_only=True)
    order_status = serializers.CharField(source="order.status", read_only=True)
    # A pending payout can be paid only once its order has been delivered
    ready_to_pay = serializers.SerializerMethodField()

    class Meta:
        model = FarmerPayout
        fields = [
            "id", "order_id", "order_status", "farmer", "farm_name", "gross_amount", "commission_amount",
            "net_amount", "status", "ready_to_pay", "transaction", "created_at", "paid_at",
        ]
        read_only_fields = fields

    def get_ready_to_pay(self, obj):
        return obj.status == FarmerPayoutStatus.PENDING and obj.order.status == OrderStatus.DELIVERED


class CommissionSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommissionSettings
        fields = ["id", "commission_rate", "effective_from", "created_at"]
        read_only_fields = ["id", "created_at"]
