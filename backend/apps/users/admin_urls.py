from rest_framework.routers import DefaultRouter
from .admin_views import DriverApprovalViewSet, FarmerApprovalViewSet, StaffViewSet, UserManagementViewSet

router = DefaultRouter()
router.register("admin/farmers", FarmerApprovalViewSet, basename="admin-farmer")
router.register("admin/drivers", DriverApprovalViewSet, basename="admin-driver")
router.register("admin/users", UserManagementViewSet, basename="admin-user")
router.register("admin/staff", StaffViewSet, basename="admin-staff")

urlpatterns = router.urls
