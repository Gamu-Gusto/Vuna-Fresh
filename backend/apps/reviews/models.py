from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class ReviewStatus(models.TextChoices):
    VISIBLE = "visible", "Visible"
    FLAGGED = "flagged", "Flagged"
    REMOVED = "removed", "Removed"


class ProductReview(models.Model):
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    buyer = models.ForeignKey(
        "users.BuyerProfile",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    helpful_count = models.PositiveIntegerField(default=0)
    helpful_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="helpful_reviews",
        blank=True,
    )
    status = models.CharField(max_length=10, choices=ReviewStatus.choices, default=ReviewStatus.VISIBLE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "product_reviews"
        ordering = ["-created_at"]
        unique_together = [("product", "buyer", "order")]

    def __str__(self):
        return f"ProductReview({self.product.name}, {self.rating}★, {self.buyer.user.email})"


class ReviewFlag(models.Model):
    review = models.ForeignKey(ProductReview, on_delete=models.CASCADE, related_name="flags")
    flagged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="review_flags",
    )
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "review_flags"
        ordering = ["-created_at"]
        unique_together = [("review", "flagged_by")]

    def __str__(self):
        return f"ReviewFlag(review={self.review_id}, by={self.flagged_by.email})"
