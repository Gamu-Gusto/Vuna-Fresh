"""
Tests for signup.

Covers:
- Self-registering as admin is refused
- Privacy policy acceptance is required, and recorded as ConsentRecords
- Business signup records consent the same way
"""
from django.test import TestCase
from rest_framework.test import APIClient

from apps.privacy.models import ConsentRecord

from .models import User

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
        for reserved in ("users.add_user", "users.change_user", "payments.change_farmerpayout", "auth.change_group"):
            self.assertFalse(manager.has_perm(reserved), reserved)
        self.assertFalse(manager.has_module_perms("auth"))
        # Ordinary users get nothing from the manager backend
        buyer = User.objects.create_user(email="b@test.com", password="x", role="customer")
        self.assertFalse(buyer.has_perm("products.add_catalogueitem"))
