from django.db import transaction
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import Address, DriverDocument, User
from .permissions import IsBuyer, IsDriver, IsDriverAccount, IsFarmerAccount
from .serializers import (
    DriverDocumentUploadSerializer,
    document_checklist,
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

        from django.core.mail import send_mail

        from .password_links import set_password_link

        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(email__iexact=serializer.validated_data["email"], is_active=True).first()
        if user is not None:
            link = set_password_link(user, portal="admin" if user.role == "admin" else None)
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


class DriverDocumentsView(APIView):
    """
    The driver's own verification documents, before or after approval.

    GET  /api/v1/users/me/driver-documents/                   — checklist and status
    POST /api/v1/users/me/driver-documents/consent/           — {granted: true|false}
    POST /api/v1/users/me/driver-documents/                   — multipart {doc_type, file}; replaces an
                                                                 earlier upload of the same type
    GET  /api/v1/users/me/driver-documents/<doc_type>/file/   — their own file
    """
    permission_classes = [IsDriverAccount]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        return Response(document_checklist(request.user.driver_profile))

    def post(self, request):
        from apps.privacy.models import ConsentRecord, ConsentType

        profile = request.user.driver_profile
        if not ConsentRecord.objects.filter(
            user=request.user, consent_type=ConsentType.DRIVER_VERIFICATION, granted=True,
        ).exists():
            return Response(
                {"error": {"code": "forbidden", "message": "Agree to the document check before uploading."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = DriverDocumentUploadSerializer(data=request.data, context={"profile": profile})
        serializer.is_valid(raise_exception=True)
        upload = serializer.validated_data["file"]
        doc_type = serializer.validated_data["doc_type"]
        with transaction.atomic():
            # Replacing: deleting the old row also deletes its file (see the post_delete signal)
            DriverDocument.objects.filter(driver=profile, doc_type=doc_type).delete()
            DriverDocument.objects.create(
                driver=profile, doc_type=doc_type, file=upload,
                original_name=upload.name[:255], content_type=upload.content_type,
            )
        return Response(document_checklist(profile), status=status.HTTP_201_CREATED)


class DriverDocumentConsentView(APIView):
    """POST /api/v1/users/me/driver-documents/consent/ — {granted}. Withdrawing it means the
    driver can't be approved; an unapproved driver's documents are then deleted by
    purge_driver_documents."""
    permission_classes = [IsDriverAccount]

    def post(self, request):
        from apps.privacy.models import ConsentRecord, ConsentType

        granted = request.data.get("granted")
        if not isinstance(granted, bool):
            return Response(
                {"error": {"code": "validation_error", "message": "Send granted: true or false."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        record, _ = ConsentRecord.objects.get_or_create(user=request.user, consent_type=ConsentType.DRIVER_VERIFICATION)
        if granted:
            record.grant()
        else:
            record.revoke()
        return Response(document_checklist(request.user.driver_profile))


class DriverDocumentFileView(APIView):
    """GET /api/v1/users/me/driver-documents/<doc_type>/file/ — the driver's own file."""
    permission_classes = [IsDriverAccount]

    def get(self, request, doc_type):
        from config.private_storage import serve_private_file

        doc = DriverDocument.objects.filter(driver__user=request.user, doc_type=doc_type).first()
        if doc is None:
            return Response({"error": {"code": "not_found", "message": "Not uploaded yet."}}, status=status.HTTP_404_NOT_FOUND)
        return serve_private_file(doc.file, doc.original_name or f"{doc_type}.pdf", doc.content_type)
