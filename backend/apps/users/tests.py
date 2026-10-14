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
