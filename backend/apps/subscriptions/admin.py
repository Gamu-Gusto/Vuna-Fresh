from django.contrib import admin
from .models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["id", "buyer", "product", "quantity", "frequency", "next_delivery_date", "status"]
    list_filter = ["status", "frequency"]
    search_fields = ["buyer__user__email", "product__name"]
    readonly_fields = ["created_at", "updated_at"]
