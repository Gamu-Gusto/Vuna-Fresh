from django.utils import timezone
from rest_framework import serializers
from .models import Category, Product, SurplusListing


class CategorySerializer(serializers.ModelSerializer):
    subcategories = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "parent_category", "subcategories"]

    def get_subcategories(self, obj):
        # Only one level deep — avoids recursive depth blowup
        children = obj.subcategories.all()
        if not children.exists():
            return []
        return CategorySerializer(children, many=True, context=self.context).data


class ProductSerializer(serializers.ModelSerializer):
    farmer_id = serializers.IntegerField(source="farmer.id", read_only=True)
    farm_name = serializers.CharField(source="farmer.farm_name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "farmer_id",
            "farm_name",
            "category",
            "category_name",
            "name",
            "description",
            "price",
            "unit",
            "stock_quantity",
            "low_stock_threshold",
            "is_available",
            "is_low_stock",
            "image_url",
            "average_rating",
            "review_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "farmer_id", "farm_name", "category_name", "is_low_stock",
            "average_rating", "review_count", "created_at", "updated_at",
        ]


class ProductWriteSerializer(serializers.ModelSerializer):
    """Used for create/update — farmer is set from the request, not the payload."""

    class Meta:
        model = Product
        fields = [
            "category",
            "name",
            "description",
            "price",
            "unit",
            "stock_quantity",
            "low_stock_threshold",
            "is_available",
            "image_url",
        ]

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        return value

    def validate_stock_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("Stock quantity cannot be negative.")
        return value

    def create(self, validated_data):
        validated_data["farmer"] = self.context["request"].user.farmer_profile
        return super().create(validated_data)


# ── Surplus listing serializers ─────────────────────────────────────────────

class SurplusListingSerializer(serializers.ModelSerializer):
    """Read serializer — the public feed and general viewing."""
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_unit = serializers.CharField(source="product.unit", read_only=True)
    product_image_url = serializers.CharField(source="product.image_url", read_only=True)
    original_price = serializers.DecimalField(source="product.price", max_digits=10, decimal_places=2, read_only=True)
    effective_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    farmer_id = serializers.IntegerField(source="farmer.id", read_only=True)
    farm_name = serializers.CharField(source="farmer.farm_name", read_only=True)

    class Meta:
        model = SurplusListing
        fields = [
            "id", "product", "product_name", "product_unit", "product_image_url",
            "farmer_id", "farm_name",
            "quantity_available", "discount_percentage", "original_price", "effective_price",
            "reason", "expires_at", "status", "created_at",
        ]
        read_only_fields = fields


class SurplusListingWriteSerializer(serializers.ModelSerializer):
    """Used for create/update — farmer is set from the request, and must own the product."""

    class Meta:
        model = SurplusListing
        fields = ["id", "product", "quantity_available", "discount_percentage", "reason", "expires_at"]
        read_only_fields = ["id"]

    def validate_product(self, value):
        request = self.context["request"]
        try:
            owns_product = value.farmer == request.user.farmer_profile
        except AttributeError:
            owns_product = False
        if not owns_product:
            raise serializers.ValidationError("You can only list surplus for your own products.")
        return value

    def validate_expires_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("expires_at must be in the future.")
        return value

    def create(self, validated_data):
        validated_data["farmer"] = self.context["request"].user.farmer_profile
        return super().create(validated_data)
