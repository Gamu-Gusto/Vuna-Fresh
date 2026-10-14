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


class DirectDepositProofInline(admin.TabularInline):
    model = DirectDepositProof
    extra = 0
    readonly_fields = ["uploaded_by", "file_url", "bank_reference_number", "status", "reviewed_by", "reviewed_at", "notes", "created_at"]
    can_delete = False


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "order", "type", "provider", "amount", "status", "created_at"]
    list_filter = ["provider", "type", "status"]
    search_fields = ["user__email", "provider_reference", "order__id"]
    readonly_fields = ["created_at"]
    inlines = [DirectDepositProofInline]


@admin.register(DirectDepositProof)
class DirectDepositProofAdmin(admin.ModelAdmin):
    list_display = ["id", "transaction", "uploaded_by", "bank_reference_number", "status", "reviewed_by", "created_at"]
    list_filter = ["status"]
    search_fields = ["uploaded_by__email", "bank_reference_number"]
    readonly_fields = ["created_at"]


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
