from datetime import date

from rest_framework import serializers

from .models import Subscription


class SubscriptionSerializer(serializers.ModelSerializer):
    """Read serializer — used for list/retrieve and action responses."""
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_unit = serializers.CharField(source="product.unit", read_only=True)
    product_price = serializers.DecimalField(source="product.price", max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "product",
            "product_name",
            "product_unit",
            "product_price",
            "quantity",
            "frequency",
            "next_delivery_date",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "product_name", "product_unit", "product_price",
            "status", "created_at", "updated_at",
        ]


class SubscriptionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ["id", "product", "quantity", "frequency", "next_delivery_date"]
        read_only_fields = ["id"]

    def validate_product(self, value):
        if not value.is_available:
            raise serializers.ValidationError("This product is not currently available.")
        return value

    def validate_next_delivery_date(self, value):
        if value < date.today():
            raise serializers.ValidationError("next_delivery_date cannot be in the past.")
        return value

    def validate(self, attrs):
        product = attrs["product"]
        quantity = attrs["quantity"]
        if quantity > product.stock_quantity:
            raise serializers.ValidationError(
                {"quantity": f"Only {product.stock_quantity} units available."}
            )
        return attrs

    def create(self, validated_data):
        validated_data["buyer"] = self.context["buyer"]
        return super().create(validated_data)
