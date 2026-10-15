from django.core.files.storage import default_storage
from django.db.models import Avg, Count, Q
from django.utils import timezone
from rest_framework import mixins, viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .archiving import RestoreError, remove_product, restore_product
from .models import CatalogueItem, Category, Product, SurplusListing, SurplusListingStatus
from .permissions import IsAdminUser, IsProductFarmer, IsProductFarmerOrAdmin
from .serializers import (
    CatalogueItemSerializer,
    CategorySerializer,
    ProductSerializer,
    ProductWriteSerializer,
    SurplusListingSerializer,
    SurplusListingWriteSerializer,
)
from .utils import InvalidImageError, save_product_image


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.filter(parent_category__isnull=True).prefetch_related("subcategories")
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsAdminUser()]


class CatalogueItemViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v1/catalogue/ — every active catalogue item, unpaginated (a few
    hundred rows), for the farmer's product picker. ?search= matches the name.
    """
    queryset = CatalogueItem.objects.filter(is_active=True).select_related(
        "category__parent_category"
    )
    serializer_class = CatalogueItemSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]


class ProductViewSet(viewsets.ModelViewSet):
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["price", "created_at", "name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = Product.objects.select_related("farmer", "category").annotate(
            average_rating=Avg(
                "reviews__rating", filter=Q(reviews__status__in=["visible", "flagged"])
            ),
            review_count=Count(
                "reviews", filter=Q(reviews__status__in=["visible", "flagged"])
            ),
        )

        # Non-farmers and unauthenticated users only see available products
        user = self.request.user
        if not user.is_authenticated or user.role not in ("farmer", "admin"):
            qs = qs.filter(is_available=True)

        # Query param filters
        # A top-level category also matches products in its subcategories
        # (catalogue products sit in subcategories, e.g. Vegetables > Root vegetables)
        category_id = self.request.query_params.get("category")
        if category_id:
            qs = qs.filter(Q(category_id=category_id) | Q(category__parent_category_id=category_id))

        farmer_id = self.request.query_params.get("farmer")
        if farmer_id:
            qs = qs.filter(farmer_id=farmer_id)

        # Lists leave out archived products unless asked for them (?archived=true,
        # the farmer's "Archived" tab). Buyers never see them: archiving also
        # makes a product unavailable, which is filtered above.
        if self.action == "list":
            qs = qs.filter(is_archived=self.request.query_params.get("archived") == "true")

        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ProductWriteSerializer
        return ProductSerializer

    def destroy(self, request, *args, **kwargs):
        """
        DELETE /products/<id>/ — "Remove". Archives a product that has been ordered
        (keeping its orders, payouts and reviews) and deletes one that never was.
        Either way it leaves the shop, carts and subscriptions (see archiving.py).
        """
        result = remove_product(self.get_object())
        return Response({"result": result}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        """POST /products/<id>/restore/ — back to the farmer's list, hidden until they list it."""
        try:
            product = restore_product(self.get_object())
        except RestoreError as e:
            return Response({"error": {"code": "bad_request", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ProductSerializer(product, context=self.get_serializer_context()).data)

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        if self.action in ("create", "upload_image"):
            return [IsAuthenticated(), IsProductFarmer()]
        # update / partial_update / destroy (remove) / restore: the product's farmer or an admin
        return [IsAuthenticated(), IsProductFarmerOrAdmin()]

    @action(
        detail=False,
        methods=["post"],
        url_path="upload_image",
        parser_classes=[MultiPartParser],
    )
    def upload_image(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response(
                {"error": {"code": "bad_request", "message": "No file provided."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            saved_path = save_product_image(file)
        except InvalidImageError as e:
            return Response(
                {"error": {"code": "bad_request", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        url = request.build_absolute_uri(default_storage.url(saved_path))
        return Response({"url": url}, status=status.HTTP_200_OK)


class SurplusListingViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET   /api/v1/surplus/            — public feed: active, unexpired listings
                                         (?product=, ?farmer=, ?reason=, ?ordering=)
    GET   /api/v1/surplus/<id>/       — listing detail
    GET   /api/v1/surplus/mine/       — farmer: all their own listings, any status
    POST  /api/v1/surplus/            — farmer creates a listing for their own product
    PATCH /api/v1/surplus/<id>/       — farmer updates their own listing
    POST  /api/v1/surplus/<id>/withdraw/ — farmer withdraws their own listing
    """
    ordering_fields = ["expires_at", "discount_percentage", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = SurplusListing.objects.select_related("product", "farmer__user")

        if self.action in ("update", "partial_update", "withdraw"):
            user = self.request.user
            if user.is_authenticated:
                try:
                    return qs.filter(farmer=user.farmer_profile)
                except AttributeError:
                    return qs.none()
            return qs.none()

        # Public feed: only what a buyer could actually still order
        qs = qs.filter(
            status=SurplusListingStatus.ACTIVE,
            expires_at__gt=timezone.now(),
            quantity_available__gt=0,
        )

        product_id = self.request.query_params.get("product")
        if product_id:
            qs = qs.filter(product_id=product_id)

        farmer_id = self.request.query_params.get("farmer")
        if farmer_id:
            qs = qs.filter(farmer_id=farmer_id)

        reason = self.request.query_params.get("reason")
        if reason:
            qs = qs.filter(reason=reason)

        ordering = self.request.query_params.get("ordering")
        if ordering and ordering.lstrip("-") in self.ordering_fields:
            qs = qs.order_by(ordering)

        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return SurplusListingWriteSerializer
        return SurplusListingSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        # create / update / partial_update / mine / withdraw are all farmer-only
        return [IsAuthenticated(), IsProductFarmer()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing = serializer.save()
        return Response(
            SurplusListingSerializer(listing, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        listing = serializer.save()
        return Response(SurplusListingSerializer(listing, context=self.get_serializer_context()).data)

    @action(detail=False, methods=["get"], url_path="mine")
    def mine(self, request):
        try:
            farmer_profile = request.user.farmer_profile
        except AttributeError:
            return Response(
                {"error": {"code": "forbidden", "message": "Only farmers have surplus listings."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        qs = SurplusListing.objects.filter(farmer=farmer_profile).select_related("product").order_by("-created_at")
        page = self.paginate_queryset(qs)
        serializer = SurplusListingSerializer(page, many=True, context=self.get_serializer_context())
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=["post"], url_path="withdraw")
    def withdraw(self, request, pk=None):
        listing = self.get_object()
        listing.status = SurplusListingStatus.WITHDRAWN
        listing.save(update_fields=["status"])
        return Response(SurplusListingSerializer(listing, context=self.get_serializer_context()).data)
