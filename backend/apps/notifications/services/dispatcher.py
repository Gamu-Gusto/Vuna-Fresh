"""
Central notification dispatch point. Other apps call `notify()` when something
happens that a user should be told about — e.g.:

    from apps.notifications.services.dispatcher import notify
    from apps.notifications.models import NotificationCategory

    notify(
        user=order.buyer.user,
        notification_type="order_status_changed",
        message="Your order #123 is out for delivery.",
        category=NotificationCategory.ORDER_UPDATES,
    )

Pass `link` (a web app path such as "/orders") to include a link in the email.
"""
import logging

from django.conf import settings
from django.core.mail import send_mail

from ..models import Notification, NotificationChannel, NotificationPreference

logger = logging.getLogger(__name__)


def notify(user, notification_type, message, category, link=None):
    """
    Logs an in-app Notification unconditionally, then — for each channel the
    user hasn't opted out of for this category — attempts delivery.

    Email goes out over SMTP (console in dev); SMS and push are still stubbed.
    """
    Notification.objects.create(user=user, type=notification_type, message=message)

    enabled_channels = set(
        NotificationPreference.objects.filter(
            user=user, category=category, enabled=True
        ).values_list("channel", flat=True)
    )

    for channel in enabled_channels:
        _dispatch(channel, user, notification_type, message, link)


def notify_admins(notification_type, message, category, link=None):
    from apps.users.models import User, UserRole

    for admin in User.objects.filter(role=UserRole.ADMIN, is_active=True):
        notify(admin, notification_type, message, category, link=link)


def _dispatch(channel, user, notification_type, message, link=None):
    """Routes to the channel's sender. SMS/push are still stubs — swap a stub's
    body for a real provider call; the dispatch logic above doesn't need to change."""
    if channel == NotificationChannel.EMAIL:
        _send_email(user, notification_type, message, link)
    elif channel == NotificationChannel.SMS:
        _send_sms(user, notification_type, message)
    elif channel == NotificationChannel.PUSH:
        _send_push(user, notification_type, message)


def _send_email(user, notification_type, message, link=None):
    body = f"Hi {user.first_name or 'there'},\n\n{message}\n"
    if link:
        body += f"\n{settings.FRONTEND_URL}{link}\n"
    body += "\nVuna Fresh — from the farm to your home.\n"
    try:
        send_mail(f"Vuna Fresh: {_subject(message)}", body, None, [user.email])
    except Exception:
        # A mail outage must never break the action that triggered the
        # notification — the in-app Notification row is already saved.
        logger.exception("Email notification failed: to=%s type=%s", user.email, notification_type)


def _subject(message):
    first_sentence = message.split(". ")[0].rstrip(".")
    return first_sentence if len(first_sentence) <= 70 else first_sentence[:67] + "..."


def _send_sms(user, notification_type, message):
    # TODO: wire up a real SMS provider (separate task). Stubbed for now.
    logger.info("[stub sms] to=%s type=%s message=%s", user.phone, notification_type, message)


def _send_push(user, notification_type, message):
    # TODO: wire up push notifications (separate task). Stubbed for now.
    logger.info("[stub push] to=user#%s type=%s message=%s", user.id, notification_type, message)
