from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    parent_category = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subcategories",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "categories"
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class CatalogueItem(models.Model):
    """
    The master list of products farmers can sell, managed by admins (CSV import
    in Django admin). A farmer's Product is always one of these, so buyers see
    one consistent name and category however many farmers sell it.
    """
    code = models.CharField(max_length=20, unique=True, help_text="e.g. SA0001")
    name = models.CharField(max_length=255, unique=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="catalogue_items",
    )
    default_unit = models.CharField(
        max_length=50,
        help_text="Pre-filled when a farmer adds this product; the farmer can change it.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Untick to stop farmers adding new listings of this product. Existing listings are unaffected.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "catalogue_items"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Farmers' listings show the catalogue's name and category, so a rename
        # or recategorisation here applies to every listing of this product.
        self.products.exclude(name=self.name, category_id=self.category_id).update(
            name=self.name, category_id=self.category_id
        )


class Product(models.Model):
    farmer = models.ForeignKey(
        "users.FarmerProfile",
        on_delete=models.CASCADE,
        related_name="products",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    # Null only for listings created before the catalogue existed; the API
    # requires it for every new listing.
    catalogue_item = models.ForeignKey(
        CatalogueItem,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="products",
    )
    # Copied from catalogue_item on save; kept on the row so listings, carts
    # and orders read them without a join.
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=50, help_text="e.g. kg, each, bunch")
    stock_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    is_available = models.BooleanField(default=True)
    image_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.farmer.farm_name})"

    def save(self, *args, **kwargs):
        if self.catalogue_item_id:
            self.name = self.catalogue_item.name
            self.category_id = self.catalogue_item.category_id
        super().save(*args, **kwargs)

    @property
    def is_low_stock(self):
        return self.stock_quantity <= self.low_stock_threshold


class SurplusReason(models.TextChoices):
    NEAR_EXPIRY = "near_expiry", "Near Expiry"
    OVERRIPE = "overripe", "Overripe"
    EXCESS_HARVEST = "excess_harvest", "Excess Harvest"
    OTHER = "other", "Other"


class SurplusListingStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    SOLD_OUT = "sold_out", "Sold Out"
    EXPIRED = "expired", "Expired"
    WITHDRAWN = "withdrawn", "Withdrawn"


class SurplusListing(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="surplus_listings")
    farmer = models.ForeignKey(
        "users.FarmerProfile",
        on_delete=models.CASCADE,
        related_name="surplus_listings",
    )
    quantity_available = models.PositiveIntegerField()
    discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    reason = models.CharField(max_length=20, choices=SurplusReason.choices)
    expires_at = models.DateTimeField()
    status = models.CharField(max_length=10, choices=SurplusListingStatus.choices, default=SurplusListingStatus.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "surplus_listings"
        ordering = ["-created_at"]

    def __str__(self):
        return f"SurplusListing({self.product.name}, {self.quantity_available}, {self.status})"

    @property
    def effective_price(self):
        """The discounted per-unit price a buyer actually pays — this is what
        gets snapshotted into CartItem.price_at_add, same as a regular product."""
        if not self.discount_percentage:
            return self.product.price
        multiplier = (Decimal("100") - self.discount_percentage) / Decimal("100")
        return (self.product.price * multiplier).quantize(Decimal("0.01"))


class WastageMetric(models.Model):
    """
    Accumulates per-farmer, per-product, per-period wastage/surplus stats.
    No write path yet (by design, for now) — this just gives the schema a place
    to land once a recalculation process is built.
    """
    farmer = models.ForeignKey(
        "users.FarmerProfile",
        on_delete=models.CASCADE,
        related_name="wastage_metrics",
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="wastage_metrics")
    period_start = models.DateField()
    period_end = models.DateField()
    quantity_listed = models.PositiveIntegerField(default=0)
    quantity_sold = models.PositiveIntegerField(default=0)
    quantity_expired_unsold = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "wastage_metrics"
        ordering = ["-period_start"]
        unique_together = [("farmer", "product", "period_start", "period_end")]

    def __str__(self):
        return f"WastageMetric({self.farmer.farm_name}, {self.product.name}, {self.period_start}–{self.period_end})"
