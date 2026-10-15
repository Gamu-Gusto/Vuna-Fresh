from django.contrib import admin
from .models import DriverReview, ProductReview, ReviewFlag


class ReviewFlagInline(admin.TabularInline):
    model = ReviewFlag
    extra = 0
    readonly_fields = ["flagged_by", "reason", "created_at"]
    can_delete = False


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ["id", "product", "buyer", "rating", "status", "helpful_count", "created_at"]
    list_filter = ["status", "rating"]
    search_fields = ["product__name", "buyer__user__email"]
    readonly_fields = ["helpful_count", "created_at", "updated_at"]
    inlines = [ReviewFlagInline]


@admin.register(ReviewFlag)
class ReviewFlagAdmin(admin.ModelAdmin):
    list_display = ["id", "review", "flagged_by", "created_at"]
    search_fields = ["review__product__name", "flagged_by__email"]
    readonly_fields = ["created_at"]


@admin.register(DriverReview)
class DriverReviewAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "driver", "buyer", "rating", "status", "created_at"]
    list_filter = ["status", "rating"]
    search_fields = ["driver__user__email", "buyer__user__email", "order__id"]
    readonly_fields = ["order", "driver", "buyer", "created_at", "updated_at"]
