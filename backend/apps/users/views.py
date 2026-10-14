from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import Address, User
from .permissions import IsBuyer, IsFarmerAccount, IsDriver
from .serializers import (
    AddressSerializer,
    BuyerProfileSerializer,
    DriverProfileSerializer,
    FarmerProfileSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserSerializer,
)


class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer


class MeView(generics.RetrieveUpdateAPIView):
    """Retrieve or update the authenticated user's own profile."""
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class AddressListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AddressSerializer

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AddressSerializer

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class BuyerProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsBuyer]
    serializer_class = BuyerProfileSerializer

    def get_object(self):
        return self.request.user.buyer_profile


class FarmerProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsFarmerAccount]
    serializer_class = FarmerProfileSerializer

    def get_object(self):
        return self.request.user.farmer_profile


class DriverProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsDriver]
    serializer_class = DriverProfileSerializer

    def get_object(self):
        return self.request.user.driver_profile


class PasswordResetRequestView(APIView):
    """
    POST /api/v1/auth/password-reset/ — {email}. Emails a reset link to the web
    app's /reset-password page. Always returns 200, whether or not the email
    is registered, so the endpoint can't be used to discover accounts.
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        import logging

        from django.conf import settings
        from django.contrib.auth.tokens import default_token_generator
        from django.core.mail import send_mail
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(email__iexact=serializer.validated_data["email"], is_active=True).first()
        if user is not None:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            link = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
            body = (
                f"Hi {user.first_name or 'there'},\n\n"
                "Someone asked to reset the password for your Vuna Fresh account. "
                f"Use this link to choose a new one:\n\n{link}\n\n"
                "The link works once and expires in 3 days. If you didn't ask for this, ignore this email.\n\n"
                "Vuna Fresh"
            )
            try:
                send_mail("Reset your Vuna Fresh password", body, None, [user.email])
            except Exception:
                logging.getLogger(__name__).exception("Password reset email failed for user #%s", user.pk)

        return Response({"detail": "If that email is registered, a reset link is on its way."})


class PasswordResetConfirmView(APIView):
    """POST /api/v1/auth/password-reset/confirm/ — {uid, token, password, password_confirm}."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        user.set_password(serializer.validated_data["password"])
        user.save(update_fields=["password"])
        return Response({"detail": "Password updated. You can now log in."})
