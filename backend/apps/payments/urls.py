from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    BankDetailsView,
    CommissionSettingsViewSet,
    DirectDepositProofViewSet,
    FarmerPayoutViewSet,
    InitiatePaymentView,
    PayFastITNView,
    PaymentMethodViewSet,
    TransactionViewSet,
)

router = DefaultRouter()
router.register("payments/methods", PaymentMethodViewSet, basename="payment-method")
router.register("payments/transactions", TransactionViewSet, basename="transaction")
router.register("payments/deposit-proofs", DirectDepositProofViewSet, basename="deposit-proof")
router.register("payments/payouts", FarmerPayoutViewSet, basename="farmer-payout")
router.register("payments/commission-settings", CommissionSettingsViewSet, basename="commission-settings")

urlpatterns = [
    path("payments/initiate/", InitiatePaymentView.as_view(), name="payments-initiate"),
    path("payments/bank-details/", BankDetailsView.as_view(), name="payments-bank-details"),
    path("payments/payfast/itn/", PayFastITNView.as_view(), name="payfast-itn"),
] + router.urls
