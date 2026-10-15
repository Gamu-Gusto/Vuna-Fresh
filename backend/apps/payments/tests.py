"""
Tests for the offline (direct deposit / EFT) payment flow.

Covers:
- PayFast is refused while PAYFAST_ENABLED is off
- Re-initiating a direct deposit reuses the open transaction and reference
- Credit-terms and already-paid orders can't be paid again
- Proof upload: file validation, one pending proof per transaction, private
  storage (only admins and the uploader can open it; admin views are logged)
- Admin approve marks the order paid; reject lets the buyer start over
- Approving needs the funds confirmed on the bank statement: amount (at least
  what's due), date, reference and an explicit "funds cleared" confirmation;
  one deposit can't pay two orders; an admin can't approve their own payment
- Farmers hear about a prepaid order only once its payment is confirmed
"""
import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.orders.models import Order, OrderItem
from apps.orders.tests import make_admin, make_buyer, make_farmer, make_product

from .models import DirectDepositProof, FarmerPayout, Transaction, TransactionStatus

MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(
    MEDIA_ROOT=MEDIA_ROOT,
    PRIVATE_MEDIA_ROOT=MEDIA_ROOT,
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

    def submit_proof(self, txn_id, reference, file=None):
        file = file or SimpleUploadedFile("proof.pdf", b"%PDF-1.4 proof", content_type="application/pdf")
        return self.client.post("/api/v1/payments/deposit-proofs/", {
            "transaction": txn_id, "file": file, "bank_reference_number": reference,
        }, format="multipart")

    def approve(self, admin_client, proof, **overrides):
        body = {
            "action": "approve", "funds_cleared": True, "amount_received": proof["amount"],
            "received_on": timezone.localdate().isoformat(),
            "bank_statement_reference": proof["expected_reference"],
            **overrides,
        }
        return admin_client.post(f"/api/v1/payments/deposit-proofs/{proof['id']}/review/", body, format="json")

    def paid_proof(self):
        """Initiate payment and submit proof as the buyer; returns the proof's API data."""
        payment = self.initiate().data
        return self.submit_proof(payment["transaction"]["id"], payment["payment"]["reference"]).data

    def admin_client(self, email="admin@test.com"):
        client = APIClient()
        client.force_authenticate(make_admin(email))
        return client

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
        payment = self.initiate().data
        bad = SimpleUploadedFile("x.exe", b"MZ", content_type="application/octet-stream")
        res = self.submit_proof(payment["transaction"]["id"], payment["payment"]["reference"], bad)
        self.assertEqual(res.status_code, 400)
        self.assertIn("file", res.data["error"]["detail"])

    def test_proof_file_is_private(self):
        from apps.privacy.models import DataAccessAuditLog

        payment = self.initiate().data
        proof = self.submit_proof(payment["transaction"]["id"], payment["payment"]["reference"]).data
        self.assertTrue(proof["has_file"])
        self.assertEqual(proof["file_url"], "")
        self.assertNotIn("file", proof)
        url = f"/api/v1/payments/deposit-proofs/{proof['id']}/file/"

        # The buyer can open their own proof; another buyer can't; nobody without logging in
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(b"".join(res.streaming_content), b"%PDF-1.4 proof")
        res.close()
        self.assertEqual(res["Cache-Control"], "private, no-store")
        other, _, _ = make_buyer("other@test.com")
        other_client = APIClient()
        other_client.force_authenticate(other)
        self.assertEqual(other_client.get(url).status_code, 404)
        self.assertEqual(APIClient().get(url).status_code, 401)
        self.assertFalse(DataAccessAuditLog.objects.exists())

        # An admin can, and that's logged against the buyer
        res = self.admin_client().get(url)
        self.assertEqual(res.status_code, 200)
        res.close()
        log = DataAccessAuditLog.objects.get()
        self.assertEqual((log.user, log.accessed_by.email), (self.buyer, "admin@test.com"))

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
        res = self.approve(admin, proof)
        self.assertEqual(res.status_code, 200)
        saved = DirectDepositProof.objects.get(pk=proof["id"])
        self.assertEqual(saved.amount_received, Decimal("100.00"))
        self.assertEqual(saved.bank_statement_reference, proof["expected_reference"])

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
        self.approve(admin, proof)
        recipients = [m.to[0] for m in mail.outbox]
        self.assertIn("buyer@test.com", recipients)
        self.assertIn("farmer@test.com", recipients)

    def test_approve_requires_funds_confirmation_details(self):
        proof = self.paid_proof()
        admin = self.admin_client()
        res = admin.post(f"/api/v1/payments/deposit-proofs/{proof['id']}/review/", {"action": "approve"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            set(res.data["error"]["detail"]),
            {"funds_cleared", "amount_received", "received_on", "bank_statement_reference"},
        )
        self.assertEqual(self.approve(admin, proof, funds_cleared=False).status_code, 400)
        self.assertEqual(self.approve(admin, proof, bank_statement_reference="  ").status_code, 400)
        future = (timezone.localdate() + timedelta(days=1)).isoformat()
        self.assertEqual(self.approve(admin, proof, received_on=future).status_code, 400)
        self.assertEqual(self.order_payment()["status"], "proof_submitted")
        self.assertFalse(FarmerPayout.objects.exists())

    def test_short_payment_cannot_be_approved(self):
        proof = self.paid_proof()
        res = self.approve(self.admin_client(), proof, amount_received="99.99")
        self.assertEqual(res.status_code, 400)
        self.assertIn("amount_received", res.data["error"]["detail"])
        self.assertEqual(self.order_payment()["status"], "proof_submitted")

    def test_overpayment_can_be_approved(self):
        proof = self.paid_proof()
        self.assertEqual(self.approve(self.admin_client(), proof, amount_received="120.00").status_code, 200)
        self.assertEqual(self.order_payment()["status"], "paid")

    def test_one_deposit_cannot_pay_two_orders(self):
        admin = self.admin_client()
        first = self.paid_proof()
        self.assertEqual(self.approve(admin, first, bank_statement_reference="SAME-DEPOSIT").status_code, 200)

        second_order = Order.objects.create(
            buyer=self.buyer_profile, delivery_address=self.address,
            subtotal=Decimal("100.00"), total=Decimal("100.00"),
        )
        payment = self.client.post(
            "/api/v1/payments/initiate/", {"order_id": second_order.id, "provider": "direct_deposit"}, format="json",
        ).data
        second = self.submit_proof(payment["transaction"]["id"], payment["payment"]["reference"]).data
        res = self.approve(admin, second, bank_statement_reference="same-deposit")
        self.assertEqual(res.status_code, 400)
        self.assertIn(f"order #{self.order.id}", str(res.data["error"]["detail"]))

    def test_admin_cannot_approve_own_payment(self):
        proof = self.paid_proof()
        DirectDepositProof.objects.filter(pk=proof["id"]).update(uploaded_by=make_admin("self@test.com"))
        admin = APIClient()
        admin.force_authenticate(DirectDepositProof.objects.get(pk=proof["id"]).uploaded_by)
        self.assertEqual(self.approve(admin, proof).status_code, 403)
        self.assertEqual(self.order_payment()["status"], "proof_submitted")

    def test_proof_cannot_be_reviewed_twice(self):
        proof = self.paid_proof()
        admin = self.admin_client()
        self.assertEqual(self.approve(admin, proof).status_code, 200)
        self.assertEqual(self.approve(admin, proof).status_code, 400)
        self.assertEqual(FarmerPayout.objects.filter(order=self.order).count(), 1)

    def test_farmer_not_told_about_order_until_payment_confirmed(self):
        from apps.notifications.models import Notification
        from apps.orders.notifications import notify_order_placed

        notify_order_placed(self.order)
        farmer_user = self.farmer_profile.user
        self.assertFalse(Notification.objects.filter(user=farmer_user).exists())

        proof = self.paid_proof()
        self.assertFalse(Notification.objects.filter(user=farmer_user).exists())
        self.approve(self.admin_client(), proof)
        self.assertTrue(Notification.objects.filter(user=farmer_user, type="order_paid").exists())
