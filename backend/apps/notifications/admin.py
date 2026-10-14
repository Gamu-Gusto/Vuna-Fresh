from django.contrib import admin
from .models import Notification, NotificationPreference


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ["user", "channel", "category", "enabled"]
    list_filter = ["channel", "category", "enabled"]
    search_fields = ["user__email"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "type", "read", "created_at"]
    list_filter = ["read", "type"]
    search_fields = ["user__email", "type", "message"]
    readonly_fields = ["created_at"]
