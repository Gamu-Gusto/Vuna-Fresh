from django.contrib import admin
from .models import BusinessBuyerDetails, BuyerAccountMember


@admin.register(BusinessBuyerDetails)
class BusinessBuyerDetailsAdmin(admin.ModelAdmin):
    list_display = ["business_name", "business_type", "credit_terms", "commission_rate", "approval_status", "created_at"]
    list_filter = ["approval_status", "business_type", "credit_terms"]
    search_fields = ["business_name", "buyer__user__email", "registration_number"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(BuyerAccountMember)
class BuyerAccountMemberAdmin(admin.ModelAdmin):
    list_display = ["user", "buyer_profile", "role", "created_at"]
    list_filter = ["role"]
    search_fields = ["user__email"]
