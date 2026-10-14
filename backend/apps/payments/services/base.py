"""
Provider abstraction. Checkout code (and the ITN/webhook views) talk to this
interface only — never branch on provider name outside of get_provider()
(see registry.py). Add a new gateway by implementing this interface and
registering it, nothing else should need to change.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class CallbackResult:
    """Standardized result of verifying an inbound payment callback/webhook."""
    success: bool
    provider_reference: Optional[str] = None
    amount: Optional[Decimal] = None
    message: str = ""
    # False means the request itself couldn't be authenticated (e.g. bad
    # signature) — the caller must not act on ANY other field in that case,
    # not even to mark the transaction failed, since none of this data can be
    # trusted to even refer to a real transaction.
    trusted: bool = True


class PaymentProvider(ABC):
    """One implementation per gateway. See payfast.py and direct_deposit.py."""

    @abstractmethod
    def initiate_payment(self, order, user):
        """
        Creates the payments.Transaction for this order/user and returns
        (transaction, payload) — payload is whatever the frontend needs to
        complete payment (PayFast redirect fields, direct deposit bank
        details, etc.). The provider decides the Transaction's initial
        status (e.g. pending for PayFast, awaiting_verification for direct
        deposit) since that's provider-specific.
        """
        raise NotImplementedError

    def verify_callback(self, request_data) -> CallbackResult:
        """
        Validates and parses an inbound webhook/callback. Only providers with
        an external callback implement this (PayFast does; direct deposit
        doesn't — it's verified via the DirectDepositProof review endpoint
        instead, so it deliberately doesn't override this).
        """
        raise NotImplementedError(f"{self.__class__.__name__} has no external callback to verify.")
