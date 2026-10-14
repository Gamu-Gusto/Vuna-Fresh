from django.contrib import admin

from .models import (
    CommissionSettings,
    DirectDepositProof,
    FarmerPayout,
    PaymentMethod,
    Transaction,
)


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ["user", "type", "provider", "is_default", "created_at"]
    list_filter = ["provider", "type", "is_default"]
    search_fields = ["user__email"]
    readonly_fields = ["created_at"]


class ViewOnlyAdminMixin:
    """
    Payment records can be looked at here but not created or changed: marking
    money as received must go through the payment review (admin Payments page),
    which checks the funds cleared, releases the order and creates payouts.
    """
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class DirectDepositProofInline(ViewOnlyAdminMixin, admin.TabularInline):
    model = DirectDepositProof
    extra = 0
    fields = readonly_fields = [
        "uploaded_by", "file_url", "bank_reference_number", "status", "reviewed_by", "reviewed_at",
        "amount_received", "received_on", "bank_statement_reference", "notes", "created_at",
    ]


@admin.register(Transaction)
class TransactionAdmin(ViewOnlyAdminMixin, admin.ModelAdmin):
    list_display = ["id", "user", "order", "type", "provider", "amount", "status", "created_at"]
    list_filter = ["provider", "type", "status"]
    search_fields = ["user__email", "provider_reference", "order__id"]
    inlines = [DirectDepositProofInline]


@admin.register(DirectDepositProof)
class DirectDepositProofAdmin(ViewOnlyAdminMixin, admin.ModelAdmin):
    list_display = [
        "id", "transaction", "uploaded_by", "bank_reference_number", "status",
        "amount_received", "received_on", "reviewed_by", "created_at",
    ]
    list_filter = ["status"]
    search_fields = ["uploaded_by__email", "bank_reference_number", "bank_statement_reference"]


@admin.register(CommissionSettings)
class CommissionSettingsAdmin(admin.ModelAdmin):
    list_display = ["commission_rate", "effective_from", "created_at"]
    ordering = ["-effective_from"]
    readonly_fields = ["created_at"]


@admin.register(FarmerPayout)
class FarmerPayoutAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "farmer", "gross_amount", "commission_amount", "net_amount", "status", "paid_at"]
    list_filter = ["status"]
    search_fields = ["farmer__farm_name", "order__id"]
    readonly_fields = ["created_at"]
