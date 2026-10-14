from rest_framework.routers import DefaultRouter
from .views import CatalogueItemViewSet, CategoryViewSet, ProductViewSet, SurplusListingViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("catalogue", CatalogueItemViewSet, basename="catalogue")
router.register("products", ProductViewSet, basename="product")
router.register("surplus", SurplusListingViewSet, basename="surplus")

urlpatterns = router.urls
