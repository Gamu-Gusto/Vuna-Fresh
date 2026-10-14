from django.core.files.storage import default_storage
from django.db import transaction as db_transaction
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    CommissionSettings,
    DirectDepositProof,
    DirectDepositProofStatus,
    FarmerPayout,
    FarmerPayoutStatus,
    PaymentMethod,
    Transaction,
    TransactionProvider,
    TransactionStatus,
    TransactionType,
)
from .permissions import IsAdminOrFarmer, IsAdminUser
from .serializers import (
    CommissionSettingsSerializer,
    DirectDepositProofSerializer,
    DirectDepositReviewSerializer,
    FarmerPayoutSerializer,
    InitiatePaymentSerializer,
    PaymentMethodSerializer,
    TransactionSerializer,
)
from .services.proof_files import InvalidProofFileError, save_proof_file
from .services.registry import get_provider
from .services.transactions import mark_payment_completed, mark_payment_failed


class PaymentMethodViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet,
):
    """
    GET    /api/v1/payments/methods/      — list own saved payment methods
    POST   /api/v1/payments/methods/      — add one
    DELETE /api/v1/payments/methods/<id>/ — remove one
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentMethodSerializer

    def get_queryset(self):
        return PaymentMethod.objects.filter(user=self.request.user)


class TransactionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    GET /api/v1/payments/transactions/      — list own transactions (admin: all, ?status=&?type=)
    GET /api/v1/payments/transactions/<id>/ — detail
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        qs = Transaction.objects.select_related("order", "user")
        user = self.request.user

        if user.role == "admin":
            status_param = self.request.query_params.get("status")
            type_param = self.request.query_params.get("type")
            if status_param:
                qs = qs.filter(status=status_param)
            if type_param:
                qs = qs.filter(type=type_param)
            return qs

        return qs.filter(user=user)


class InitiatePaymentView(APIView):
    """
    POST /api/v1/payments/initiate/ — {order_id, provider: "payfast"|"direct_deposit"}

    Creates the Transaction for an already-placed order (see apps.orders —
    untouched by this app) and returns whatever the frontend needs next:
    PayFast redirect fields, or direct deposit bank details + reference.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = InitiatePaymentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        order = serializer._order
        provider_name = serializer.validated_data["provider"]

        provider = get_provider(provider_name)
        transaction, payload = provider.initiate_payment(order, request.user)

        return Response(
            {"transaction": TransactionSerializer(transaction).data, "payment": payload},
            status=status.HTTP_201_CREATED,
        )


class BankDetailsView(APIView):
    """GET /api/v1/payments/bank-details/ — the account to pay into (e.g. for invoices)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .services.direct_deposit import platform_bank_details
        return Response(platform_bank_details())


class PayFastITNView(APIView):
    """
    POST /api/v1/payments/payfast/itn/ — PayFast's server-to-server Instant
    Transaction Notification. No auth — PayFast can't authenticate as a
    platform user, the signature check IS the authentication here. Always
    returns 200 (PayFast retries on anything else), even when we ignore the
    request as untrusted or can't find a matching Transaction.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        provider = get_provider("payfast")
        result = provider.verify_callback(request.data)

        if not result.trusted:
            # Signature didn't match — don't touch the database on the
            # strength of unauthenticated data, not even m_payment_id.
            return Response(status=status.HTTP_200_OK)

        m_payment_id = request.data.get("m_payment_id")
        txn = Transaction.objects.filter(pk=m_payment_id, provider=TransactionProvider.PAYFAST).first()
        if txn is None:
            return Response(status=status.HTTP_200_OK)

        if result.success:
            already_paid = txn.status == TransactionStatus.COMPLETED  # PayFast retries ITNs
            mark_payment_completed(txn, provider_reference=result.provider_reference)
            if txn.order and not already_paid:
                from apps.orders.notifications import notify_order_paid
                notify_order_paid(txn.order)
        else:
            mark_payment_failed(txn)

        return Response(status=status.HTTP_200_OK)


class DirectDepositProofViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet,
):
    """
    GET  /api/v1/payments/deposit-proofs/            — list own proofs (admin: all)
    POST /api/v1/payments/deposit-proofs/             — buyer uploads proof against their transaction
    GET  /api/v1/payments/deposit-proofs/<id>/        — detail
    POST /api/v1/payments/deposit-proofs/upload/      — multipart file upload, returns {url} for file_url
    GET  /api/v1/payments/deposit-proofs/pending/     — admin-only: proofs awaiting review
    POST /api/v1/payments/deposit-proofs/<id>/review/ — admin-only: approve or reject
    """
    permission_classes = [IsAuthenticated]
    serializer_class = DirectDepositProofSerializer

    def get_queryset(self):
        qs = DirectDepositProof.objects.select_related("transaction", "uploaded_by", "reviewed_by")
        user = self.request.user
        if user.role == "admin":
            return qs
        return qs.filter(uploaded_by=user)

    def get_permissions(self):
        if self.action in ("pending", "review"):
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        from apps.notifications.models import NotificationCategory
        from apps.notifications.services.dispatcher import notify_admins

        proof = serializer.save()
        notify_admins(
            "direct_deposit_submitted",
            f"Proof of payment submitted for order #{proof.transaction.order_id} "
            f"(R{proof.transaction.amount}, ref {proof.bank_reference_number}).",
            NotificationCategory.ORDER_UPDATES, link="/admin/payments",
        )

    @action(detail=False, methods=["post"], url_path="upload", parser_classes=[MultiPartParser])
    def upload(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response(
                {"error": {"code": "bad_request", "message": "No file provided."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            saved_path = save_proof_file(file)
        except InvalidProofFileError as e:
            return Response(
                {"error": {"code": "bad_request", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        url = request.build_absolute_uri(default_storage.url(saved_path))
        return Response({"url": url}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="pending")
    def pending(self, request):
        qs = DirectDepositProof.objects.filter(
            status=DirectDepositProofStatus.PENDING_REVIEW
        ).select_related("transaction", "uploaded_by").order_by("created_at")
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=["post"], url_path="review")
    def review(self, request, pk=None):
        """
        approve: {action, funds_cleared: true, amount_received, received_on,
                  bank_statement_reference, notes?} — only after checking the
                  money has cleared in the bank account (see DirectDepositReviewSerializer).
        reject:  {action, notes}
        """
        with db_transaction.atomic():
            # Lock the row so two admins reviewing at once can't both act on it
            proof = DirectDepositProof.objects.select_for_update().select_related(
                "transaction"
            ).get(pk=self.get_object().pk)
            if proof.status != DirectDepositProofStatus.PENDING_REVIEW:
                return Response(
                    {"error": {"code": "bad_request", "message": "This proof has already been reviewed."}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if request.user.id in (proof.uploaded_by_id, proof.transaction.user_id):
                return Response(
                    {"error": {"code": "forbidden", "message": "Another admin must review a payment you made yourself."}},
                    status=status.HTTP_403_FORBIDDEN,
                )

            serializer = DirectDepositReviewSerializer(data=request.data, context={"proof": proof})
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            proof.reviewed_by = request.user
            proof.reviewed_at = timezone.now()
            proof.notes = data.get("notes", "")
            approved = data["action"] == "approve"

            if approved:
                proof.status = DirectDepositProofStatus.VERIFIED
                proof.amount_received = data["amount_received"]
                proof.received_on = data["received_on"]
                proof.bank_statement_reference = data["bank_statement_reference"]
                proof.save(update_fields=[
                    "reviewed_by", "reviewed_at", "notes", "status",
                    "amount_received", "received_on", "bank_statement_reference",
                ])
                mark_payment_completed(proof.transaction)
            else:
                proof.status = DirectDepositProofStatus.REJECTED
                proof.save(update_fields=["reviewed_by", "reviewed_at", "notes", "status"])
                mark_payment_failed(proof.transaction)

        if approved:
            self._notify_approval(proof)
            if proof.transaction.order:
                from apps.orders.notifications import notify_order_paid
                notify_order_paid(proof.transaction.order)
        else:
            self._notify_rejection(proof)

        return Response(DirectDepositProofSerializer(proof).data)

    def _notify_approval(self, proof):
        from apps.notifications.models import NotificationCategory
        from apps.notifications.services.dispatcher import notify

        notify(
            user=proof.uploaded_by,
            notification_type="direct_deposit_verified",
            message=f"Payment received for order #{proof.transaction.order_id}. Thank you!",
            category=NotificationCategory.ORDER_UPDATES,
            link="/orders",
        )

    def _notify_rejection(self, proof):
        from apps.notifications.models import NotificationCategory
        from apps.notifications.services.dispatcher import notify

        reason = proof.notes or "no reason given"
        notify(
            user=proof.uploaded_by,
            notification_type="direct_deposit_rejected",
            message=f"Your proof of payment for order #{proof.transaction.order_id} "
                    f"(ref {proof.bank_reference_number}) was rejected: {reason}. Please pay again or contact support.",
            category=NotificationCategory.ORDER_UPDATES,
            link=f"/orders/{proof.transaction.order_id}/pay",
        )


class FarmerPayoutViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    GET  /api/v1/payments/payouts/               — admin: list payouts (?status=);
                                                     farmer: list own payouts (read-only)
    GET  /api/v1/payments/payouts/pending/        — admin: list pending payouts
    POST /api/v1/payments/payouts/<id>/mark_paid/ — admin: mark paid, creates the
                                                     farmer_payout Transaction. Manual —
                                                     not automated disbursement.
    """
    serializer_class = FarmerPayoutSerializer

    def get_permissions(self):
        if self.action == "list":
            return [IsAuthenticated(), IsAdminOrFarmer()]
        return [IsAuthenticated(), IsAdminUser()]

    def get_queryset(self):
        qs = FarmerPayout.objects.select_related("farmer__user", "order")
        if self.request.user.role == "farmer":
            qs = qs.filter(farmer__user=self.request.user)
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    @action(detail=False, methods=["get"], url_path="pending")
    def pending(self, request):
        qs = self.get_queryset().filter(status=FarmerPayoutStatus.PENDING)
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=["post"], url_path="mark_paid")
    def mark_paid(self, request, pk=None):
        payout = self.get_object()
        if payout.status == FarmerPayoutStatus.PAID:
            return Response(
                {"error": {"code": "bad_request", "message": "This payout has already been marked as paid."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payout_transaction = Transaction.objects.create(
            order=payout.order,
            user=payout.farmer.user,
            provider=TransactionProvider.INTERNAL,
            type=TransactionType.FARMER_PAYOUT,
            amount=payout.net_amount,
            status=TransactionStatus.COMPLETED,
        )
        payout.transaction = payout_transaction
        payout.status = FarmerPayoutStatus.PAID
        payout.paid_at = timezone.now()
        payout.save(update_fields=["transaction", "status", "paid_at"])

        return Response(FarmerPayoutSerializer(payout).data)


class CommissionSettingsViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    GET  /api/v1/payments/commission-settings/ — admin: list all (current + historical)
    POST /api/v1/payments/commission-settings/ — admin: set a new rate (with effective_from)
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = CommissionSettingsSerializer
    queryset = CommissionSettings.objects.all()
