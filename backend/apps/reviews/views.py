from django.db.models import Avg, Count, F
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import DriverReview, ProductReview, ReviewStatus
from .permissions import IsAdminUser, IsBuyer, IsDriver, IsFarmer, IsReviewOwner
from .serializers import (
    DriverReviewSerializer,
    DriverReviewWriteSerializer,
    ProductReviewSerializer,
    ProductReviewUpdateSerializer,
    ProductReviewWriteSerializer,
    ReviewFlagSerializer,
    ReviewStatusUpdateSerializer,
)


class ProductReviewViewSet(viewsets.ModelViewSet):
    """
    GET    /api/v1/reviews/                — list reviews (?product=, ?rating=, ?ordering=)
    GET    /api/v1/reviews/<id>/           — review detail
    POST   /api/v1/reviews/                — create a review for a delivered order (customer)
    PATCH  /api/v1/reviews/<id>/           — edit own review
    DELETE /api/v1/reviews/<id>/           — delete own review
    POST   /api/v1/reviews/<id>/mark_helpful/ — increment helpful_count (once per user)
    POST   /api/v1/reviews/<id>/flag/         — flag a review
    GET    /api/v1/reviews/flagged/           — admin: list flagged reviews
    POST   /api/v1/reviews/<id>/set_status/   — admin: change review status
    GET    /api/v1/reviews/my_products/       — farmer: reviews for their own products
    """
    ordering_fields = ["rating", "created_at", "helpful_count"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = ProductReview.objects.select_related(
            "product", "buyer__user", "order"
        ).prefetch_related("helpful_by")

        user = self.request.user

        if self.action in ("update", "partial_update", "destroy"):
            # Scoped to every buyer account this user can reach — IsReviewOwner
            # narrows further (blocks viewer-role members from writing).
            if user.is_authenticated:
                from apps.buyers.resolvers import get_accessible_buyer_profiles
                accessible_ids = [p.id for p in get_accessible_buyer_profiles(user)]
                return qs.filter(buyer_id__in=accessible_ids)
            return qs.none()

        if not (user.is_authenticated and user.role == "admin"):
            qs = qs.exclude(status=ReviewStatus.REMOVED)

        product_id = self.request.query_params.get("product")
        if product_id:
            qs = qs.filter(product_id=product_id)

        rating = self.request.query_params.get("rating")
        if rating:
            qs = qs.filter(rating=rating)

        ordering = self.request.query_params.get("ordering")
        if ordering and ordering.lstrip("-") in self.ordering_fields:
            qs = qs.order_by(ordering)

        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return ProductReviewWriteSerializer
        if self.action in ("update", "partial_update"):
            return ProductReviewUpdateSerializer
        return ProductReviewSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        if self.action == "create":
            return [IsAuthenticated(), IsBuyer()]
        if self.action in ("update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsReviewOwner()]
        if self.action in ("flagged", "set_status"):
            return [IsAuthenticated(), IsAdminUser()]
        if self.action == "my_products":
            return [IsAuthenticated(), IsFarmer()]
        # mark_helpful, flag
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        return Response(
            ProductReviewSerializer(review, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        return Response(ProductReviewSerializer(review, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"], url_path="mark_helpful")
    def mark_helpful(self, request, pk=None):
        review = self.get_object()
        if not review.helpful_by.filter(pk=request.user.pk).exists():
            review.helpful_by.add(request.user)
            ProductReview.objects.filter(pk=review.pk).update(helpful_count=F("helpful_count") + 1)
            review.refresh_from_db(fields=["helpful_count"])
        return Response(ProductReviewSerializer(review, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"], url_path="flag")
    def flag(self, request, pk=None):
        review = self.get_object()
        serializer = ReviewFlagSerializer(
            data=request.data, context={"request": request, "review": review}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="flagged")
    def flagged(self, request):
        qs = ProductReview.objects.filter(status=ReviewStatus.FLAGGED).select_related(
            "product", "buyer__user", "order"
        ).prefetch_related("helpful_by").order_by("-created_at")
        page = self.paginate_queryset(qs)
        serializer = ProductReviewSerializer(page, many=True, context=self.get_serializer_context())
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=["post"], url_path="set_status")
    def set_status(self, request, pk=None):
        review = self.get_object()
        serializer = ReviewStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review.status = serializer.validated_data["status"]
        review.save(update_fields=["status"])
        return Response(ProductReviewSerializer(review, context=self.get_serializer_context()).data)

    @action(detail=False, methods=["get"], url_path="my_products")
    def my_products(self, request):
        qs = ProductReview.objects.filter(
            product__farmer=request.user.farmer_profile
        ).exclude(status=ReviewStatus.REMOVED).select_related(
            "product", "buyer__user", "order"
        ).prefetch_related("helpful_by").order_by("-created_at")
        page = self.paginate_queryset(qs)
        serializer = ProductReviewSerializer(page, many=True, context=self.get_serializer_context())
        return self.get_paginated_response(serializer.data)


def driver_rating_summary(driver_reviews):
    """{"average": 4.5 or None, "count": n} over visible ratings only."""
    agg = driver_reviews.exclude(status=ReviewStatus.REMOVED).aggregate(average=Avg("rating"), count=Count("id"))
    average = round(agg["average"], 1) if agg["average"] is not None else None
    return {"average": average, "count": agg["count"]}


class DriverReviewViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet,
):
    """
    POST /api/v1/driver-reviews/                  — buyer rates the driver of a delivered order (once)
    GET  /api/v1/driver-reviews/                  — buyer: own ratings; driver: ratings received
                                                     (without who wrote them); admin: all (?driver=)
    GET  /api/v1/driver-reviews/summary/          — driver: own average rating; admin: ?driver=<id>
    POST /api/v1/driver-reviews/<id>/set_status/  — admin: hide (removed) or restore (visible) a rating
    """

    def get_queryset(self):
        qs = DriverReview.objects.select_related("driver__user", "buyer__user")
        user = self.request.user
        if user.role == "admin":
            driver_id = self.request.query_params.get("driver")
            return qs.filter(driver_id=driver_id) if driver_id else qs
        if user.role == "driver":
            return qs.filter(driver__user=user).exclude(status=ReviewStatus.REMOVED)
        from apps.buyers.resolvers import get_accessible_buyer_profiles
        return qs.filter(buyer_id__in=[p.id for p in get_accessible_buyer_profiles(user)])

    def get_serializer_class(self):
        return DriverReviewWriteSerializer if self.action == "create" else DriverReviewSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsBuyer()]
        if self.action == "set_status":
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        return Response(
            DriverReviewSerializer(review, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        if request.user.role == "admin":
            driver_id = request.query_params.get("driver")
            if not driver_id:
                return Response(
                    {"error": {"code": "bad_request", "message": "Pass ?driver=<id>."}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(driver_rating_summary(DriverReview.objects.filter(driver_id=driver_id)))
        if request.user.role == "driver":
            return Response(driver_rating_summary(DriverReview.objects.filter(driver__user=request.user)))
        return Response(
            {"error": {"code": "forbidden", "message": "Only drivers and admins can see rating summaries."}},
            status=status.HTTP_403_FORBIDDEN,
        )

    @action(detail=True, methods=["post"], url_path="set_status")
    def set_status(self, request, pk=None):
        review = self.get_object()
        serializer = ReviewStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review.status = serializer.validated_data["status"]
        review.save(update_fields=["status"])
        return Response(DriverReviewSerializer(review, context=self.get_serializer_context()).data)
