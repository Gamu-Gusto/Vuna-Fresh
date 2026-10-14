from django.contrib import admin
from .models import Cart, CartItem, Order, OrderItem, OrderStatusHistory


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ["price_at_add"]


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["buyer", "status", "created_at"]
    list_filter = ["status"]
    inlines = [CartItemInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["product", "farmer", "quantity", "price_at_purchase"]


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ["status", "changed_at", "changed_by"]
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "buyer", "status", "total", "created_at"]
    list_filter = ["status"]
    search_fields = ["buyer__user__email"]
    readonly_fields = ["subtotal", "delivery_fee", "total", "created_at"]
    inlines = [OrderItemInline, OrderStatusHistoryInline]
