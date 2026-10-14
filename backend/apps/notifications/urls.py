from rest_framework.routers import DefaultRouter
from .views import NotificationPreferenceViewSet, NotificationViewSet

router = DefaultRouter()
# Registered before "notifications" so /notifications/preferences/ isn't
# swallowed by the /notifications/<pk>/ detail route.
router.register("notifications/preferences", NotificationPreferenceViewSet, basename="notification-preference")
router.register("notifications", NotificationViewSet, basename="notification")

urlpatterns = router.urls
