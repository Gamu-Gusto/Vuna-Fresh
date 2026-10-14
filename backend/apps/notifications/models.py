from django.conf import settings
from django.db import models


class NotificationChannel(models.TextChoices):
    EMAIL = "email", "Email"
    SMS = "sms", "SMS"
    PUSH = "push", "Push"


class NotificationCategory(models.TextChoices):
    ORDER_UPDATES = "order_updates", "Order Updates"
    MARKETING = "marketing", "Marketing"
    ISSUE_UPDATES = "issue_updates", "Issue Updates"


# Sensible defaults applied when a user's preference rows are first created —
# see signals.py. Marketing is opt-in; operational categories are opt-out.
DEFAULT_ENABLED_BY_CATEGORY = {
    NotificationCategory.ORDER_UPDATES: True,
    NotificationCategory.ISSUE_UPDATES: True,
    NotificationCategory.MARKETING: False,
}


class NotificationPreference(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    channel = models.CharField(max_length=10, choices=NotificationChannel.choices)
    category = models.CharField(max_length=20, choices=NotificationCategory.choices)
    enabled = models.BooleanField(default=True)

    class Meta:
        db_table = "notification_preferences"
        unique_together = [("user", "channel", "category")]
        ordering = ["channel", "category"]

    def __str__(self):
        state = "on" if self.enabled else "off"
        return f"NotificationPreference({self.user.email}, {self.channel}, {self.category}, {state})"


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    type = models.CharField(max_length=50)
    message = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification({self.user.email}, {self.type})"
