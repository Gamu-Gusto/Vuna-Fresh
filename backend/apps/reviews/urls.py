from rest_framework.routers import DefaultRouter
from .views import DriverReviewViewSet, ProductReviewViewSet

router = DefaultRouter()
router.register("reviews", ProductReviewViewSet, basename="review")
router.register("driver-reviews", DriverReviewViewSet, basename="driver-review")

urlpatterns = router.urls
