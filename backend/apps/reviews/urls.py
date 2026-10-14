from rest_framework.routers import DefaultRouter
from .views import ProductReviewViewSet

router = DefaultRouter()
router.register("reviews", ProductReviewViewSet, basename="review")

urlpatterns = router.urls
