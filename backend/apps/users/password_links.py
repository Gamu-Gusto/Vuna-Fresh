"""One-time links to the web app's /reset-password page, for resets and new staff invitations."""
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlencode, urlsafe_base64_encode


def set_password_link(user, portal=None):
    """
    A link that lets `user` choose a password once. It stops working as soon as
    the password changes, or after PASSWORD_RESET_TIMEOUT (3 days by default).
    `portal` ("admin") tells the page which log-in link to offer afterwards.
    """
    params = {
        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
        "token": default_token_generator.make_token(user),
    }
    if portal:
        params["for"] = portal
    return f"{settings.FRONTEND_URL}/reset-password?{urlencode(params)}"
