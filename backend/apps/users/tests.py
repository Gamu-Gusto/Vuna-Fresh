"""
Tests for signup and accounts.

Covers:
- Self-registering as admin is refused
- Privacy policy acceptance is required, and recorded as ConsentRecords
- Business signup records consent the same way
- Super admin and managers
- Driver verification: age and identity at signup, consented private documents,
  the approval rule, and 30-day deletion of documents no longer needed
"""
import io
import shutil
import tempfile
from datetime import date, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.privacy.models import ConsentRecord, DataAccessAuditLog

from .models import DriverDocument, DriverProfile, User

SIGNUP = {
    "email": "new@test.com",
    "first_name": "New",
    "last_name": "User",
    "phone": "0820000000",
    "role": "customer",
    "password": "Str0ng-Passw0rd!",
    "password_confirm": "Str0ng-Passw0rd!",
    "accept_privacy_policy": True,
}


class RegisterTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def register(self, **overrides):
        return self.client.post("/api/v1/auth/register/", {**SIGNUP, **overrides}, format="json")

    def test_cannot_self_register_as_admin(self):
        res = self.register(role="admin")
        self.assertEqual(res.status_code, 400)
        self.assertFalse(User.objects.filter(email=SIGNUP["email"]).exists())

    def test_privacy_policy_must_be_accepted(self):
        self.assertEqual(self.register(accept_privacy_policy=False).status_code, 400)
        data = {k: v for k, v in SIGNUP.items() if k != "accept_privacy_policy"}
        self.assertEqual(self.client.post("/api/v1/auth/register/", data, format="json").status_code, 400)

    def test_signup_records_consent(self):
        self.assertEqual(self.register(marketing_opt_in=True).status_code, 201)
        consents = dict(
            ConsentRecord.objects.filter(user__email=SIGNUP["email"]).values_list("consent_type", "granted")
        )
        self.assertEqual(consents, {"data_collection": True, "marketing": True})

    def test_marketing_defaults_to_not_granted(self):
        self.register()
        marketing = ConsentRecord.objects.get(user__email=SIGNUP["email"], consent_type="marketing")
        self.assertFalse(marketing.granted)

    def test_business_signup_records_consent(self):
        res = self.client.post("/api/v1/buyers/business/signup/", {
            **{k: SIGNUP[k] for k in ("email", "first_name", "last_name", "password", "password_confirm")},
            "accept_privacy_policy": True,
            "business_name": "Spaza One",
            "business_type": "spaza_shop",
            "street_address": "1 Main Rd",
            "city": "Soweto",
            "province": "Gauteng",
            "postal_code": "1804",
        }, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(ConsentRecord.objects.filter(
            user__email=SIGNUP["email"], consent_type="data_collection", granted=True,
        ).exists())


class PasswordResetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="reset@test.com", password="Old-Passw0rd!", first_name="Reset", last_name="Me", role="customer",
        )

    def reset_link_params(self):
        from urllib.parse import parse_qs, urlparse

        from django.core import mail

        self.assertEqual(len(mail.outbox), 1)
        link = next(line for line in mail.outbox[0].body.splitlines() if "/reset-password?" in line)
        query = parse_qs(urlparse(link).query)
        return query["uid"][0], query["token"][0]

    def test_unknown_email_gets_same_response_and_no_email(self):
        from django.core import mail

        res = self.client.post("/api/v1/auth/password-reset/", {"email": "nobody@test.com"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_full_reset_flow(self):
        res = self.client.post("/api/v1/auth/password-reset/", {"email": "RESET@test.com"}, format="json")
        self.assertEqual(res.status_code, 200)
        uid, token = self.reset_link_params()

        res = self.client.post("/api/v1/auth/password-reset/confirm/", {
            "uid": uid, "token": token, "password": "New-Passw0rd!", "password_confirm": "New-Passw0rd!",
        }, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("New-Passw0rd!"))

        # The token is single-use: the password change invalidates it.
        res = self.client.post("/api/v1/auth/password-reset/confirm/", {
            "uid": uid, "token": token, "password": "Other-Passw0rd!", "password_confirm": "Other-Passw0rd!",
        }, format="json")
        self.assertEqual(res.status_code, 400)

    def test_bad_token_rejected(self):
        self.client.post("/api/v1/auth/password-reset/", {"email": "reset@test.com"}, format="json")
        uid, _ = self.reset_link_params()
        res = self.client.post("/api/v1/auth/password-reset/confirm/", {
            "uid": uid, "token": "bad-token", "password": "New-Passw0rd!", "password_confirm": "New-Passw0rd!",
        }, format="json")
        self.assertEqual(res.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Old-Passw0rd!"))


class SuperAdminAndManagerTests(TestCase):
    """
    The super admin (admin role + superuser) can do everything; a manager (admin
    role, not superuser) can do everything except manage admin accounts and pay
    farmers, in the API and in Django admin.
    """

    def setUp(self):
        from django.core import mail

        self.mail = mail
        self.super_admin = User.objects.create_superuser(
            email="boss@test.com", password="TestPass123!", first_name="Gamu", last_name="D",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.super_admin)

    def add_manager(self, email="manager@test.com"):
        return self.client.post("/api/v1/admin/staff/", {
            "email": email, "first_name": "Thabo", "last_name": "M",
        }, format="json")

    def manager_client(self):
        manager = User.objects.get(email="manager@test.com")
        client = APIClient()
        client.force_authenticate(manager)
        return client, manager

    def test_super_admin_adds_manager_who_sets_own_password(self):
        res = self.add_manager()
        self.assertEqual(res.status_code, 201)
        manager = User.objects.get(email="manager@test.com")
        self.assertEqual((manager.role, manager.is_staff, manager.is_superuser), ("admin", True, False))
        self.assertFalse(manager.has_usable_password())
        self.assertIn("for=admin", res.data["set_password_link"])
        self.assertIn("manager@test.com", [m.to[0] for m in self.mail.outbox])

        # The link is a normal password-reset link: following it sets the password
        from urllib.parse import parse_qs, urlparse
        params = parse_qs(urlparse(res.data["set_password_link"]).query)
        res = APIClient().post("/api/v1/auth/password-reset/confirm/", {
            "uid": params["uid"][0], "token": params["token"][0],
            "password": "NewPass456!x", "password_confirm": "NewPass456!x",
        }, format="json")
        self.assertEqual(res.status_code, 200)
        res = APIClient().post("/api/v1/auth/token/", {"email": "manager@test.com", "password": "NewPass456!x"}, format="json")
        self.assertEqual(res.status_code, 200)

    def test_duplicate_email_refused(self):
        self.add_manager()
        self.assertEqual(self.add_manager("MANAGER@test.com").status_code, 400)

    def test_me_endpoint_says_who_is_super_admin(self):
        self.add_manager()
        manager_client, _ = self.manager_client()
        self.assertTrue(self.client.get("/api/v1/users/me/").data["is_super_admin"])
        self.assertFalse(manager_client.get("/api/v1/users/me/").data["is_super_admin"])

    def test_manager_cannot_manage_the_team(self):
        self.add_manager()
        manager_client, manager = self.manager_client()
        self.assertEqual(manager_client.get("/api/v1/admin/staff/").status_code, 403)
        self.assertEqual(manager_client.post("/api/v1/admin/staff/", {
            "email": "x@test.com", "first_name": "X", "last_name": "Y",
        }, format="json").status_code, 403)
        # Nor deactivate the super admin through the general users page
        res = manager_client.post(f"/api/v1/admin/users/{self.super_admin.id}/deactivate/")
        self.assertEqual(res.status_code, 403)
        self.super_admin.refresh_from_db()
        self.assertTrue(self.super_admin.is_active)

    def test_manager_still_has_admin_access(self):
        self.add_manager()
        manager_client, _ = self.manager_client()
        self.assertEqual(manager_client.get("/api/v1/admin/users/").status_code, 200)
        self.assertEqual(manager_client.get("/api/v1/admin/farmers/").status_code, 200)
        self.assertEqual(manager_client.get("/api/v1/payments/payouts/").status_code, 200)

    def test_super_admin_deactivates_and_reactivates_manager(self):
        manager_id = self.add_manager().data["staff"]["id"]
        res = self.client.post(f"/api/v1/admin/staff/{manager_id}/deactivate/")
        self.assertEqual((res.status_code, res.data["status"]), (200, "deactivated"))
        self.assertEqual(self.client.post(f"/api/v1/admin/staff/{manager_id}/set_password_link/").status_code, 400)
        res = self.client.post(f"/api/v1/admin/staff/{manager_id}/reactivate/")
        self.assertEqual((res.status_code, res.data["status"]), (200, "active"))
        self.assertIn("token=", self.client.post(f"/api/v1/admin/staff/{manager_id}/set_password_link/").data["set_password_link"])

    def test_super_admin_account_cannot_be_changed_on_team_page(self):
        res = self.client.post(f"/api/v1/admin/staff/{self.super_admin.id}/deactivate/")
        self.assertEqual(res.status_code, 403)

    def test_django_admin_permissions(self):
        self.add_manager()
        _, manager = self.manager_client()
        manager = User.objects.get(pk=manager.pk)  # fresh permission cache
        self.assertTrue(manager.has_perm("products.add_catalogueitem"))
        self.assertTrue(manager.has_perm("users.change_farmerprofile"))
        self.assertTrue(manager.has_perm("users.view_user"))
        self.assertTrue(manager.has_perm("payments.view_commissionsettings"))
        for reserved in (
            "users.add_user", "users.change_user", "payments.change_farmerpayout",
            "payments.add_commissionsettings", "payments.change_commissionsettings", "auth.change_group",
        ):
            self.assertFalse(manager.has_perm(reserved), reserved)
        self.assertFalse(manager.has_module_perms("auth"))
        # Ordinary users get nothing from the manager backend
        buyer = User.objects.create_user(email="b@test.com", password="x", role="customer")
        self.assertFalse(buyer.has_perm("products.add_catalogueitem"))


    def test_only_super_admin_changes_commission_rate(self):
        self.add_manager()
        manager_client, _ = self.manager_client()
        body = {"commission_rate": "10.00", "effective_from": "2026-01-01T00:00:00Z"}
        self.assertEqual(manager_client.post("/api/v1/payments/commission-settings/", body, format="json").status_code, 403)
        self.assertEqual(manager_client.get("/api/v1/payments/commission-settings/").status_code, 200)
        self.assertEqual(self.client.post("/api/v1/payments/commission-settings/", body, format="json").status_code, 201)


def sa_id_for(dob, sequence="5009"):
    """A valid 13-digit SA ID number for a date of birth (Luhn check digit worked out)."""
    body = dob.strftime("%y%m%d") + sequence + "08"
    for check in "0123456789":
        total = 0
        for i, ch in enumerate(reversed(body + check)):
            digit = int(ch)
            if i % 2 == 1:
                digit = digit * 2 - 9 if digit * 2 > 9 else digit * 2
            total += digit
        if total % 10 == 0:
            return body + check
    raise AssertionError("no valid check digit")


def pdf(name="doc.pdf", body=b"%PDF-1.4 document"):
    return SimpleUploadedFile(name, body, content_type="application/pdf")


class DriverVerificationTests(TestCase):
    """
    Driver signup: 21+, SA ID (valid, matching the date of birth) or passport;
    then a consented document checklist by nationality, stored privately; an
    admin can only approve a complete application; documents of rejected,
    withdrawn or abandoned applications are deleted after 30 days.
    """

    SA_DOCS = ["sa_drivers_licence", "sa_id", "vehicle_registration", "roadworthy_certificate",
               "licence_disc", "proof_of_address", "proof_of_bank_account"]

    def setUp(self):
        self.private_root = tempfile.mkdtemp()
        override = override_settings(PRIVATE_MEDIA_ROOT=self.private_root)
        override.enable()
        self.addCleanup(override.disable)
        self.addCleanup(shutil.rmtree, self.private_root, True)

        self.client = APIClient()
        self.dob = date(1995, 3, 14)
        self.admin = User.objects.create_superuser(email="boss@test.com", password="TestPass123!")
        self.admin_client = APIClient()
        self.admin_client.force_authenticate(self.admin)

    def signup(self, **overrides):
        data = {
            "email": "driver@test.com", "first_name": "Sipho", "last_name": "N", "phone": "0820000000",
            "password": "StrongPass!2026", "password_confirm": "StrongPass!2026", "role": "driver",
            "accept_privacy_policy": True, "date_of_birth": self.dob.isoformat(),
            "nationality": "sa_citizen", "id_number": sa_id_for(self.dob),
            "vehicle_type": "Bakkie", "vehicle_registration": "GP 12 AB",
            **overrides,
        }
        return self.client.post("/api/v1/auth/register/", data, format="json")

    def driver_client(self):
        client = APIClient()
        client.force_authenticate(User.objects.get(email="driver@test.com"))
        return client

    def profile(self):
        return User.objects.get(email="driver@test.com").driver_profile

    def consent_and_upload(self, client, doc_types):
        client.post("/api/v1/users/me/driver-documents/consent/", {"granted": True}, format="json")
        for t in doc_types:
            res = client.post(
                "/api/v1/users/me/driver-documents/", {"doc_type": t, "file": pdf(f"{t}.pdf")}, format="multipart",
            )
            self.assertEqual(res.status_code, 201, res.data)

    def approve(self):
        return self.admin_client.post(
            f"/api/v1/admin/drivers/{self.profile().id}/review/", {"action": "approve"}, format="json",
        )

    def purge(self):
        call_command("purge_driver_documents", stdout=io.StringIO())

    # Signup

    def test_sa_signup_saves_identity_and_vehicle(self):
        self.assertEqual(self.signup().status_code, 201)
        profile = self.profile()
        self.assertEqual(
            (profile.date_of_birth, profile.nationality, profile.vehicle_type, profile.id_number, profile.passport_number),
            (self.dob, "sa_citizen", "Bakkie", sa_id_for(self.dob), ""),
        )

    def test_under_21_refused(self):
        today = date.today()
        young = date(today.year - 20, today.month, min(today.day, 28))
        res = self.signup(date_of_birth=young.isoformat(), id_number=sa_id_for(young))
        self.assertEqual(res.status_code, 400)
        self.assertIn("date_of_birth", res.data["error"]["detail"])
        self.assertFalse(User.objects.filter(email="driver@test.com").exists())

    def test_sa_id_must_be_valid_and_match_date_of_birth(self):
        good = sa_id_for(self.dob)
        bad_check_digit = good[:-1] + str((int(good[-1]) + 1) % 10)
        self.assertEqual(self.signup(id_number=bad_check_digit).status_code, 400)
        self.assertEqual(self.signup(id_number="12345").status_code, 400)
        res = self.signup(id_number=sa_id_for(date(1990, 1, 1)))
        self.assertIn("match", str(res.data["error"]["detail"]["id_number"]))

    def test_foreign_national_needs_passport(self):
        res = self.signup(nationality="foreign_national", id_number="")
        self.assertIn("passport_number", res.data["error"]["detail"])
        res = self.signup(nationality="foreign_national", id_number="", passport_number="ZW1234567")
        self.assertEqual(res.status_code, 201)
        self.assertEqual((self.profile().passport_number, self.profile().id_number), ("ZW1234567", ""))

    def test_customer_signup_unaffected(self):
        res = self.client.post("/api/v1/auth/register/", {
            "email": "buyer@test.com", "first_name": "A", "last_name": "B", "phone": "1",
            "password": "StrongPass!2026", "password_confirm": "StrongPass!2026", "role": "customer",
            "accept_privacy_policy": True,
        }, format="json")
        self.assertEqual(res.status_code, 201)

    # Documents

    def test_checklist_depends_on_nationality(self):
        self.signup()
        sa = [i["doc_type"] for i in self.driver_client().get("/api/v1/users/me/driver-documents/").data["items"]]
        self.assertEqual(sa, self.SA_DOCS)
        User.objects.filter(email="driver@test.com").delete()
        self.signup(nationality="foreign_national", id_number="", passport_number="P1")
        foreign = [i["doc_type"] for i in self.driver_client().get("/api/v1/users/me/driver-documents/").data["items"]]
        self.assertEqual(foreign[:3], ["foreign_drivers_licence", "passport", "work_permit"])
        self.assertNotIn("sa_id", foreign)

    def test_upload_needs_consent_and_valid_file(self):
        self.signup()
        client = self.driver_client()
        url = "/api/v1/users/me/driver-documents/"
        self.assertEqual(client.post(url, {"doc_type": "sa_id", "file": pdf()}, format="multipart").status_code, 403)
        client.post(f"{url}consent/", {"granted": True}, format="json")
        self.assertTrue(ConsentRecord.objects.get(consent_type="driver_verification").granted)
        exe = SimpleUploadedFile("x.exe", b"MZ", content_type="application/octet-stream")
        self.assertEqual(client.post(url, {"doc_type": "sa_id", "file": exe}, format="multipart").status_code, 400)
        # Not on this (South African) driver's list
        self.assertEqual(client.post(url, {"doc_type": "passport", "file": pdf()}, format="multipart").status_code, 400)

    def test_reupload_replaces_and_deletes_old_file(self):
        self.signup()
        client = self.driver_client()
        self.consent_and_upload(client, ["sa_id"])
        old = DriverDocument.objects.get()
        old_name, storage = old.file.name, old.file.storage
        self.consent_and_upload(client, ["sa_id"])
        self.assertEqual(DriverDocument.objects.count(), 1)
        self.assertFalse(storage.exists(old_name))

    def test_files_are_private(self):
        self.signup()
        client = self.driver_client()
        self.consent_and_upload(client, ["sa_id"])
        res = client.get("/api/v1/users/me/driver-documents/sa_id/file/")
        self.assertEqual((res.status_code, b"".join(res.streaming_content)), (200, b"%PDF-1.4 document"))
        res.close()
        self.assertEqual(APIClient().get("/api/v1/users/me/driver-documents/sa_id/file/").status_code, 401)
        with self.assertRaises(ValueError):  # a private file has no URL at all
            DriverDocument.objects.get().file.url

    # Admin review

    def test_cannot_approve_until_complete(self):
        self.signup()
        client = self.driver_client()
        profile = self.profile()

        self.assertIn("agreed to the document check", self.approve().data["error"]["message"])
        self.consent_and_upload(client, self.SA_DOCS[:-1])
        self.assertIn("1 required document(s) not uploaded", self.approve().data["error"]["message"])
        self.consent_and_upload(client, self.SA_DOCS[-1:])

        # Admin rejects the proof of address: the driver sees why, approval is blocked
        doc = DriverDocument.objects.get(doc_type="proof_of_address")
        res = self.admin_client.post(
            f"/api/v1/admin/drivers/{profile.id}/documents/{doc.id}/review/",
            {"action": "reject", "note": "Older than 3 months"}, format="json",
        )
        self.assertEqual(res.data["verification"]["rejected"], ["Proof of address"])
        items = client.get("/api/v1/users/me/driver-documents/").data["items"]
        item = next(i for i in items if i["doc_type"] == "proof_of_address")
        self.assertEqual((item["document"]["status"], item["document"]["review_note"]), ("rejected", "Older than 3 months"))
        self.assertIn("need a new upload", self.approve().data["error"]["message"])

        # Viewing a document is logged against the driver
        res = self.admin_client.get(f"/api/v1/admin/drivers/{profile.id}/documents/{doc.id}/file/")
        self.assertEqual(res.status_code, 200)
        res.close()  # release the file (Windows locks open files)
        self.assertEqual(DataAccessAuditLog.objects.get().user.email, "driver@test.com")

        # A new upload, then approval goes through and every document is accepted
        self.consent_and_upload(client, ["proof_of_address"])
        res = self.approve()
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(res.data["is_approved"])
        self.assertEqual(set(DriverDocument.objects.values_list("status", flat=True)), {"accepted"})

    def test_drivers_cannot_use_admin_document_views(self):
        self.signup()
        self.consent_and_upload(self.driver_client(), ["sa_id"])
        doc = DriverDocument.objects.get()
        url = f"/api/v1/admin/drivers/{self.profile().id}/documents/{doc.id}/file/"
        self.assertEqual(self.driver_client().get(url).status_code, 403)

    # Retention

    def test_purge_30_days_after_rejection(self):
        self.signup()
        self.consent_and_upload(self.driver_client(), ["sa_id"])
        doc = DriverDocument.objects.get()
        name, storage = doc.file.name, doc.file.storage

        self.purge()
        self.assertEqual(DriverDocument.objects.count(), 1)  # recent and in progress: kept

        self.admin_client.post(
            f"/api/v1/admin/drivers/{self.profile().id}/review/", {"action": "reject", "reason": "Incomplete"}, format="json",
        )
        self.purge()
        self.assertEqual(DriverDocument.objects.count(), 1)  # rejected today: kept for 30 days
        DriverProfile.objects.update(rejected_at=timezone.now() - timedelta(days=31))
        self.purge()
        self.assertEqual(DriverDocument.objects.count(), 0)
        self.assertFalse(storage.exists(name))

    def test_purge_when_consent_withdrawn_or_abandoned(self):
        self.signup()
        client = self.driver_client()
        self.consent_and_upload(client, ["sa_id"])
        client.post("/api/v1/users/me/driver-documents/consent/", {"granted": False}, format="json")
        self.purge()
        self.assertEqual(DriverDocument.objects.count(), 0)

        # Abandoned: incomplete, with nothing happening for 31 days
        self.consent_and_upload(client, ["sa_id"])
        long_ago = timezone.now() - timedelta(days=31)
        DriverDocument.objects.update(uploaded_at=long_ago)
        User.objects.filter(email="driver@test.com").update(date_joined=long_ago)
        self.purge()
        self.assertEqual(DriverDocument.objects.count(), 0)

    def test_approved_drivers_documents_are_kept(self):
        self.signup()
        self.consent_and_upload(self.driver_client(), self.SA_DOCS)
        self.assertEqual(self.approve().status_code, 200)
        DriverDocument.objects.update(uploaded_at=timezone.now() - timedelta(days=400))
        self.purge()
        self.assertEqual(DriverDocument.objects.count(), len(self.SA_DOCS))
