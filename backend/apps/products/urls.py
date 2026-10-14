from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProductViewSet, SurplusListingViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("products", ProductViewSet, basename="product")
router.register("surplus", SurplusListingViewSet, basename="surplus")

urlpatterns = router.urls
