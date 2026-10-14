from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import DEFAULT_ENABLED_BY_CATEGORY, NotificationChannel, NotificationCategory, NotificationPreference


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_default_notification_preferences(sender, instance, created, **kwargs):
    """Gives every new user one preference row per channel/category so settings
    are never unset — see DEFAULT_ENABLED_BY_CATEGORY for the defaults."""
    if not created:
        return

    NotificationPreference.objects.bulk_create(
        [
            NotificationPreference(
                user=instance,
                channel=channel,
                category=category,
                enabled=DEFAULT_ENABLED_BY_CATEGORY[category],
            )
            for channel in NotificationChannel.values
            for category in NotificationCategory.values
        ]
    )
