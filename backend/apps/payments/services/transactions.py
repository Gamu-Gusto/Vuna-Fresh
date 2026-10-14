"""
Single shared path for moving a buyer payment Transaction to completed/failed
— called from both the PayFast ITN view and the direct-deposit proof review
endpoint, so the "completed -> trigger payout calculation" step lives in
exactly one place regardless of which payment path got it there.
"""
from django.db import transaction as db_transaction

from ..models import TransactionStatus, TransactionType
from .payouts import calculate_and_create_payouts


def mark_payment_completed(txn, provider_reference=None):
    with db_transaction.atomic():
        if txn.status == TransactionStatus.COMPLETED:
            return txn  # already processed — avoid recalculating/duplicating payouts

        txn.status = TransactionStatus.COMPLETED
        update_fields = ["status"]
        if provider_reference:
            txn.provider_reference = provider_reference
            update_fields.append("provider_reference")
        txn.save(update_fields=update_fields)

        if txn.type == TransactionType.PAYMENT:
            calculate_and_create_payouts(txn)

    return txn


def mark_payment_failed(txn):
    if txn.status == TransactionStatus.FAILED:
        return txn
    txn.status = TransactionStatus.FAILED
    txn.save(update_fields=["status"])
    return txn
