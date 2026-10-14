"""
PayFast integration. Signature spec: concatenate name=value pairs in the
EXACT order they appear (PayFast does not sort them), URL-encoded with
spaces as '+', skipping blank values, then append &passphrase=... if one is
set, then MD5 the whole string. This module uses that identical algorithm
both to sign our own outgoing request and to verify incoming ITN posts —
same function, so the two can never drift apart.
"""
import hashlib
from decimal import Decimal, InvalidOperation
from urllib.parse import quote_plus

from django.conf import settings

from ..models import Transaction, TransactionProvider, TransactionStatus, TransactionType
from .base import CallbackResult, PaymentProvider

SANDBOX_PROCESS_URL = "https://sandbox.payfast.co.za/eng/process"
LIVE_PROCESS_URL = "https://www.payfast.co.za/eng/process"


def generate_signature(fields, passphrase=""):
    """fields: an ordered mapping (dict, preserving insertion order) of the
    exact fields being sent/received, EXCLUDING 'signature' itself."""
    pairs = []
    for key, value in fields.items():
        if key == "signature":
            continue
        if value is None or value == "":
            continue
        pairs.append(f"{key}={quote_plus(str(value))}")
    param_string = "&".join(pairs)
    if passphrase:
        param_string += f"&passphrase={quote_plus(passphrase)}"
    return hashlib.md5(param_string.encode("utf-8")).hexdigest()


class PayFastProvider(PaymentProvider):
    def __init__(self):
        self.merchant_id = settings.PAYFAST_MERCHANT_ID
        self.merchant_key = settings.PAYFAST_MERCHANT_KEY
        self.passphrase = settings.PAYFAST_PASSPHRASE
        self.sandbox = settings.PAYFAST_SANDBOX
        self.notify_url = settings.PAYFAST_NOTIFY_URL
        self.return_url = settings.PAYFAST_RETURN_URL
        self.cancel_url = settings.PAYFAST_CANCEL_URL

    def initiate_payment(self, order, user):
        transaction = Transaction.objects.create(
            order=order,
            user=user,
            provider=TransactionProvider.PAYFAST,
            type=TransactionType.PAYMENT,
            amount=order.total,
            status=TransactionStatus.PENDING,
        )

        # m_payment_id is OUR reference, echoed back verbatim on the ITN —
        # that's how the webhook maps back to this Transaction.
        fields = {
            "merchant_id": self.merchant_id,
            "merchant_key": self.merchant_key,
            "return_url": self.return_url,
            "cancel_url": self.cancel_url,
            "notify_url": self.notify_url,
            "m_payment_id": str(transaction.id),
            "amount": f"{order.total:.2f}",
            "item_name": f"Vuna Fresh Order #{order.id}"[:100],
        }
        fields["signature"] = generate_signature(fields, self.passphrase)

        process_url = SANDBOX_PROCESS_URL if self.sandbox else LIVE_PROCESS_URL
        return transaction, {"process_url": process_url, "fields": fields}

    def verify_callback(self, request_data):
        # request_data is a QueryDict for PayFast's real (form-encoded) ITN posts.
        # dict(query_dict) is a trap: since QueryDict is itself a dict subclass,
        # CPython's dict() constructor takes a fast path that copies its raw
        # internal {key: [v1, v2]} storage directly, bypassing QueryDict's own
        # __getitem__ override that would normally unwrap to the scalar value.
        # .dict() is QueryDict's own correct scalar conversion; plain dicts
        # (e.g. in tests) don't have it, so fall back to dict() for those.
        data = request_data.dict() if hasattr(request_data, "dict") else dict(request_data)
        received_signature = data.get("signature")
        expected_signature = generate_signature(data, self.passphrase)

        if not received_signature or received_signature != expected_signature:
            return CallbackResult(success=False, message="Invalid signature", trusted=False)

        payment_status = data.get("payment_status")
        pf_payment_id = data.get("pf_payment_id")
        amount_gross = data.get("amount_gross")

        try:
            amount = Decimal(amount_gross) if amount_gross not in (None, "") else None
        except InvalidOperation:
            amount = None

        if payment_status != "COMPLETE":
            return CallbackResult(
                success=False, provider_reference=pf_payment_id, amount=amount,
                message=f"payment_status={payment_status!r}", trusted=True,
            )

        return CallbackResult(
            success=True, provider_reference=pf_payment_id, amount=amount, message="OK", trusted=True,
        )
