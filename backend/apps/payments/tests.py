"""
Tests for the offline (direct deposit / EFT) payment flow.

Covers:
- PayFast is refused while PAYFAST_ENABLED is off
- Re-initiating a direct deposit reuses the open transaction and reference
- Credit-terms and already-paid orders can't be paid again
- Proof upload: file validation, one pending proof per transaction
- Admin approve marks the order paid; reject lets the buyer start over
"""
import shutil
import tempfile
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.orders.models import Order, OrderItem
from apps.orders.tests import make_admin, make_buyer, make_farmer, make_product

from .models import FarmerPayout, Transaction, TransactionStatus

MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(
    MEDIA_ROOT=MEDIA_ROOT,
    DEFAULT_FILE_STORAGE="django.core.files.storage.FileSystemStorage",
    PAYFAST_ENABLED=False,
)
class DirectDepositFlowTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.buyer, self.buyer_profile, self.address = make_buyer("buyer@test.com")
        _, self.farmer_profile = make_farmer("farmer@test.com")
        product = make_product(self.farmer_profile, price="50.00")
        self.order = Order.objects.create(
            buyer=self.buyer_profile, delivery_address=self.address,
            subtotal=Decimal("100.00"), total=Decimal("100.00"),
        )
        OrderItem.objects.create(
            order=self.order, product=product, farmer=self.farmer_profile,
            quantity=2, price_at_purchase=Decimal("50.00"),
        )
        self.client = APIClient()
        self.client.force_authenticate(self.buyer)

    def initiate(self, provider="direct_deposit"):
        return self.client.post(
            "/api/v1/payments/initiate/", {"order_id": self.order.id, "provider": provider}, format="json",
        )

    def submit_proof(self, txn_id, reference):
        return self.client.post("/api/v1/payments/deposit-proofs/", {
            "transaction": txn_id, "file_url": "http://localhost/media/deposit-proofs/x.pdf",
            "bank_reference_number": reference,
        }, format="json")

    def order_payment(self):
        return self.client.get(f"/api/v1/orders/{self.order.id}/").data["payment"]

    def test_payfast_refused_while_disabled(self):
        res = self.initiate("payfast")
        self.assertEqual(res.status_code, 400)
        self.assertFalse(Transaction.objects.exists())

    def test_initiate_returns_bank_details_and_is_reused(self):
        first = self.initiate()
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.data["payment"]["amount"], "100.00")
        self.assertTrue(first.data["payment"]["reference"].startswith(f"VF-{self.order.id}-"))

        second = self.initiate()
        self.assertEqual(second.data["payment"]["reference"], first.data["payment"]["reference"])
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(self.order_payment()["status"], "awaiting_payment")

    def test_credit_terms_order_cannot_be_prepaid(self):
        self.order.payment_terms = "net_30"
        self.order.save()
        self.assertEqual(self.initiate().status_code, 400)
        self.assertEqual(self.order_payment()["status"], "credit")

    def test_upload_rejects_wrong_file_type(self):
        bad = SimpleUploadedFile("x.exe", b"MZ", content_type="application/octet-stream")
        res = self.client.post("/api/v1/payments/deposit-proofs/upload/", {"file": bad}, format="multipart")
        self.assertEqual(res.status_code, 400)

        good = SimpleUploadedFile("proof.pdf", b"%PDF-1.4", content_type="application/pdf")
        res = self.client.post("/api/v1/payments/deposit-proofs/upload/", {"file": good}, format="multipart")
        self.assertEqual(res.status_code, 200)
        self.assertIn("/deposit-proofs/", res.data["url"])

    def test_only_one_pending_proof_per_transaction(self):
        payment = self.initiate().data
        txn_id, ref = payment["transaction"]["id"], payment["payment"]["reference"]
        self.assertEqual(self.submit_proof(txn_id, ref).status_code, 201)
        self.assertEqual(self.submit_proof(txn_id, ref).status_code, 400)
        self.assertEqual(self.order_payment()["status"], "proof_submitted")

    def test_approve_marks_paid_and_blocks_repayment(self):
        payment = self.initiate().data
        proof = self.submit_proof(payment["transaction"]["id"], payment["payment"]["reference"]).data

        admin = APIClient()
        admin.force_authenticate(make_admin("admin@test.com"))
        res = admin.post(f"/api/v1/payments/deposit-proofs/{proof['id']}/review/", {"action": "approve"}, format="json")
        self.assertEqual(res.status_code, 200)

        self.assertEqual(self.order_payment()["status"], "paid")
        self.assertTrue(FarmerPayout.objects.filter(order=self.order).exists())
        self.assertEqual(self.initiate().status_code, 400)

    def test_reject_lets_buyer_pay_again_with_new_reference(self):
        payment = self.initiate().data
        proof = self.submit_proof(payment["transaction"]["id"], payment["payment"]["reference"]).data

        admin = APIClient()
        admin.force_authenticate(make_admin("admin@test.com"))
        admin.post(
            f"/api/v1/payments/deposit-proofs/{proof['id']}/review/",
            {"action": "reject", "notes": "Amount not received"}, format="json",
        )
        self.assertEqual(Transaction.objects.get().status, TransactionStatus.FAILED)
        self.assertEqual(self.order_payment()["status"], "unpaid")

        retry = self.initiate().data
        self.assertNotEqual(retry["payment"]["reference"], payment["payment"]["reference"])

    def test_payment_events_send_emails(self):
        from django.core import mail

        admin_user = make_admin("admin@test.com")
        payment = self.initiate().data
        mail.outbox.clear()

        proof = self.submit_proof(payment["transaction"]["id"], payment["payment"]["reference"]).data
        self.assertIn(admin_user.email, [m.to[0] for m in mail.outbox])

        mail.outbox.clear()
        admin = APIClient()
        admin.force_authenticate(admin_user)
        admin.post(f"/api/v1/payments/deposit-proofs/{proof['id']}/review/", {"action": "approve"}, format="json")
        recipients = [m.to[0] for m in mail.outbox]
        self.assertIn("buyer@test.com", recipients)
        self.assertIn("farmer@test.com", recipients)
