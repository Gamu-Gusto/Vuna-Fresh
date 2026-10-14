from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    BusinessBuyerApprovalViewSet,
    BusinessBuyerSignupView,
    BuyerAccountMemberViewSet,
    MyBusinessDetailsView,
)

router = DefaultRouter()
router.register("buyers/admin/business", BusinessBuyerApprovalViewSet, basename="business-buyer-approval")
router.register("buyers/members", BuyerAccountMemberViewSet, basename="buyer-account-member")

urlpatterns = [
    path("buyers/business/signup/", BusinessBuyerSignupView.as_view(), name="business-buyer-signup"),
    path("buyers/me/business/", MyBusinessDetailsView.as_view(), name="my-business-details"),
] + router.urls
