from rest_framework.routers import DefaultRouter
from .views import ConsentViewSet, DataAccessRequestViewSet, DataAccessAuditLogViewSet

router = DefaultRouter()
router.register("privacy/consent", ConsentViewSet, basename="consent")
router.register("privacy/data-requests", DataAccessRequestViewSet, basename="data-request")
router.register("privacy/audit-log", DataAccessAuditLogViewSet, basename="audit-log")

urlpatterns = router.urls
