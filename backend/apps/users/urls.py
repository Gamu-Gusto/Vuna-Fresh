from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenBlacklistView

from .views import (
    AddressDetailView,
    AddressListCreateView,
    BuyerProfileView,
    DriverDocumentConsentView,
    DriverDocumentFileView,
    DriverDocumentsView,
    DriverProfileView,
    FarmerProfileView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
)

urlpatterns = [
    # Auth
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/token/blacklist/", TokenBlacklistView.as_view(), name="token_blacklist"),
    path("auth/password-reset/", PasswordResetRequestView.as_view(), name="password_reset"),
    path("auth/password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    # User
    path("users/me/", MeView.as_view(), name="me"),
    # Addresses
    path("users/me/addresses/", AddressListCreateView.as_view(), name="address-list"),
    path("users/me/addresses/<int:pk>/", AddressDetailView.as_view(), name="address-detail"),
    # Profiles
    path("users/me/profile/buyer/", BuyerProfileView.as_view(), name="buyer-profile"),
    path("users/me/profile/farmer/", FarmerProfileView.as_view(), name="farmer-profile"),
    path("users/me/profile/driver/", DriverProfileView.as_view(), name="driver-profile"),
    # Driver verification documents (before and after approval)
    path("users/me/driver-documents/", DriverDocumentsView.as_view(), name="driver-documents"),
    path("users/me/driver-documents/consent/", DriverDocumentConsentView.as_view(), name="driver-documents-consent"),
    path("users/me/driver-documents/<str:doc_type>/file/", DriverDocumentFileView.as_view(), name="driver-document-file"),
]
