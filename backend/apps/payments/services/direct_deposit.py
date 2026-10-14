import uuid

from django.conf import settings

from ..models import Transaction, TransactionProvider, TransactionStatus, TransactionType
from .base import PaymentProvider


def platform_bank_details():
    """The Vuna Fresh bank account buyers pay into (EFT / direct deposit)."""
    return {
        "bank_name": settings.PLATFORM_BANK_NAME,
        "account_holder": settings.PLATFORM_BANK_ACCOUNT_HOLDER,
        "account_number": settings.PLATFORM_BANK_ACCOUNT_NUMBER,
        "branch_code": settings.PLATFORM_BANK_BRANCH_CODE,
        "account_type": settings.PLATFORM_BANK_ACCOUNT_TYPE,
    }


class DirectDepositProvider(PaymentProvider):
    def initiate_payment(self, order, user):
        # Re-initiating (e.g. the buyer reopening the payment page) reuses the
        # open transaction so the buyer keeps the same reference. A rejected
        # proof marks the transaction failed, so the retry gets a fresh one.
        transaction = Transaction.objects.filter(
            order=order,
            provider=TransactionProvider.DIRECT_DEPOSIT,
            type=TransactionType.PAYMENT,
            status=TransactionStatus.AWAITING_VERIFICATION,
        ).first()

        if transaction is None:
            transaction = Transaction.objects.create(
                order=order,
                user=user,
                provider=TransactionProvider.DIRECT_DEPOSIT,
                type=TransactionType.PAYMENT,
                amount=order.total,
                status=TransactionStatus.AWAITING_VERIFICATION,
                provider_reference=f"VF-{order.id}-{uuid.uuid4().hex[:6].upper()}",
            )
        reference = transaction.provider_reference

        bank_details = {
            **platform_bank_details(),
            "reference": reference,
            "amount": str(transaction.amount),
        }

        return transaction, bank_details

    # No verify_callback override — there is no external webhook for direct
    # deposit. Verification happens through the DirectDepositProof review
    # endpoint (views.DirectDepositProofViewSet.review), which calls
    # services.transactions.mark_payment_completed()/mark_payment_failed()
    # directly instead of going through a provider callback.
