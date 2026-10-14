from rest_framework import serializers

from .models import ProductReview, ReviewFlag, ReviewStatus


class ProductReviewSerializer(serializers.ModelSerializer):
    """Read serializer — used for list/retrieve and any other read-only response."""
    buyer_name = serializers.CharField(source="buyer.user.full_name", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    is_helpful_by_me = serializers.SerializerMethodField()

    class Meta:
        model = ProductReview
        fields = [
            "id",
            "product",
            "product_name",
            "buyer_name",
            "order",
            "rating",
            "comment",
            "helpful_count",
            "is_helpful_by_me",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_is_helpful_by_me(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        # helpful_by is prefetched by the viewset queryset, so this is in-memory, not a query.
        return any(user.pk == request.user.pk for user in obj.helpful_by.all())


class ProductReviewWriteSerializer(serializers.ModelSerializer):
    """Used for POST /reviews/ — verifies the buyer actually received this product."""

    class Meta:
        model = ProductReview
        fields = ["id", "product", "order", "rating", "comment"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        from apps.orders.models import OrderStatus
        from apps.buyers.resolvers import user_can_act_for_buyer_profile

        request = self.context["request"]
        product = attrs["product"]
        order = attrs["order"]

        # The review is attributed to whichever buyer account placed and
        # received the order — a business account's members can review on the
        # account's behalf (viewers excluded) without needing their own
        # purchase of the same product.
        if not user_can_act_for_buyer_profile(request.user, order.buyer, require_write=True):
            raise serializers.ValidationError("This order does not belong to you.")
        if order.status != OrderStatus.DELIVERED:
            raise serializers.ValidationError("You can only review products from delivered orders.")
        if not order.items.filter(product=product).exists():
            raise serializers.ValidationError("This order does not contain this product.")
        if ProductReview.objects.filter(product=product, buyer=order.buyer, order=order).exists():
            raise serializers.ValidationError("You have already reviewed this product for this order.")

        self._buyer = order.buyer
        return attrs

    def create(self, validated_data):
        validated_data["buyer"] = self._buyer
        return super().create(validated_data)


class ProductReviewUpdateSerializer(serializers.ModelSerializer):
    """Used for PATCH — only the rating/comment can be edited, not product/order/customer."""

    class Meta:
        model = ProductReview
        fields = ["rating", "comment"]


class ReviewFlagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewFlag
        fields = ["id", "review", "reason", "created_at"]
        read_only_fields = ["id", "review", "created_at"]

    def validate(self, attrs):
        review = self.context["review"]
        user = self.context["request"].user
        if ReviewFlag.objects.filter(review=review, flagged_by=user).exists():
            raise serializers.ValidationError("You have already flagged this review.")
        return attrs

    def create(self, validated_data):
        review = self.context["review"]
        user = self.context["request"].user

        flag = ReviewFlag.objects.create(review=review, flagged_by=user, **validated_data)

        if review.status == ReviewStatus.VISIBLE:
            review.status = ReviewStatus.FLAGGED
            review.save(update_fields=["status"])

        return flag


class ReviewStatusUpdateSerializer(serializers.Serializer):
    """Admin-only — moves a review between visible/flagged/removed."""
    status = serializers.ChoiceField(choices=ReviewStatus.choices)
