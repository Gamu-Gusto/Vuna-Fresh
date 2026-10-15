from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from apps.privacy.consent import SignupConsentFields, pop_signup_consent, record_signup_consent

from .driver_verification import (
    ALLOWED_DOCUMENT_TYPES, DOCUMENT_HINTS, MAX_DOCUMENT_SIZE, MINIMUM_DRIVER_AGE,
    DocumentType, Nationality, age_on, sa_id_date_of_birth,
)
from .models import User, Address, BuyerProfile, DriverDocument, FarmerProfile, DriverProfile, UserRole


class RegisterSerializer(SignupConsentFields, serializers.ModelSerializer):
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all(), message="A user with this email already exists.")]
    )
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    farm_name = serializers.CharField(write_only=True, required=False, allow_blank=False, max_length=255)
    farm_location = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=255, default="")
    # Drivers only (see driver_verification.py): identity, age and vehicle
    date_of_birth = serializers.DateField(write_only=True, required=False)
    nationality = serializers.ChoiceField(choices=Nationality.choices, write_only=True, required=False)
    id_number = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=13, default="")
    passport_number = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=20, default="")
    vehicle_type = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=100, default="")
    vehicle_registration = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=20, default="")

    class Meta:
        model = User
        fields = [
            "email", "first_name", "last_name", "phone", "role",
            "password", "password_confirm", "farm_name", "farm_location",
            "date_of_birth", "nationality", "id_number", "passport_number",
            "vehicle_type", "vehicle_registration",
            "accept_privacy_policy", "marketing_opt_in",
        ]

    def validate_role(self, value):
        # Admins are created by other admins (createsuperuser / Django admin), never self-registered.
        if value == UserRole.ADMIN:
            raise serializers.ValidationError("Choose customer, farmer or driver.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        if attrs.get("role") == "farmer" and not attrs.get("farm_name", "").strip():
            raise serializers.ValidationError({"farm_name": "Farm name is required when registering as a farmer."})
        if attrs.get("role") == UserRole.DRIVER:
            self._validate_driver(attrs)
        return attrs

    def _validate_driver(self, attrs):
        errors = {}
        dob, nationality = attrs.get("date_of_birth"), attrs.get("nationality")
        id_number = attrs.get("id_number", "").replace(" ", "")
        passport = attrs.get("passport_number", "").strip()
        if not dob:
            errors["date_of_birth"] = "Enter your date of birth."
        elif age_on(dob) < MINIMUM_DRIVER_AGE:
            errors["date_of_birth"] = f"Drivers must be {MINIMUM_DRIVER_AGE} or older."
        if not nationality:
            errors["nationality"] = "Choose whether you're a South African citizen or a foreign national."
        elif nationality == Nationality.SA_CITIZEN:
            try:
                id_dob = sa_id_date_of_birth(id_number)
            except ValueError as e:
                errors["id_number"] = str(e)
            else:
                if dob and id_dob != dob:
                    errors["id_number"] = "This ID number doesn't match the date of birth you entered."
        elif not passport:
            errors["passport_number"] = "Enter your passport number."
        if not attrs.get("vehicle_type", "").strip():
            errors["vehicle_type"] = "Tell us what vehicle you'll deliver with."
        if not attrs.get("vehicle_registration", "").strip():
            errors["vehicle_registration"] = "Enter the vehicle's registration number."
        if errors:
            raise serializers.ValidationError(errors)
        # Keep only the identity number that applies
        attrs["id_number"] = id_number if nationality == Nationality.SA_CITIZEN else ""
        attrs["passport_number"] = "" if nationality == Nationality.SA_CITIZEN else passport

    def create(self, validated_data):
        farm_name = validated_data.pop("farm_name", "")
        farm_location = validated_data.pop("farm_location", "")
        driver_fields = {
            key: validated_data.pop(key, None)
            for key in ("date_of_birth", "nationality", "id_number", "passport_number",
                        "vehicle_type", "vehicle_registration")
        }
        marketing_opt_in = pop_signup_consent(validated_data)
        user = User.objects.create_user(**validated_data)
        record_signup_consent(user, marketing_opt_in)
        if user.role == "farmer":
            FarmerProfile.objects.create(user=user, farm_name=farm_name, farm_location=farm_location)
        elif user.role == "customer":
            BuyerProfile.objects.create(user=user)
        elif user.role == "driver":
            DriverProfile.objects.create(
                user=user, **{k: v.strip() if isinstance(v, str) else v for k, v in driver_fields.items() if v},
            )
        return user


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    # Admin accounts only: the super admin, as opposed to a manager
    is_super_admin = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name",
            "phone", "role", "status", "date_joined", "is_super_admin",
        ]
        read_only_fields = ["id", "email", "role", "status", "date_joined", "is_super_admin"]

    def get_is_super_admin(self, obj):
        return obj.role == "admin" and obj.is_superuser


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "id", "label", "street_address", "suburb", "city",
            "province", "postal_code", "country", "is_default",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class BuyerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BuyerProfile
        fields = ["buyer_type", "preferred_delivery_address"]
        read_only_fields = ["buyer_type"]


class FarmerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmerProfile
        fields = [
            "id", "farm_name", "farm_description", "farm_location",
            "is_approved", "approved_at", "rejection_reason",
        ]
        read_only_fields = ["id", "is_approved", "approved_at", "rejection_reason"]


class DriverProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverProfile
        fields = [
            "vehicle_type", "vehicle_registration",
            "is_approved", "approved_at", "is_available",
        ]
        read_only_fields = ["is_approved", "approved_at"]


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_str
        from django.utils.http import urlsafe_base64_decode

        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(attrs["uid"])), is_active=True)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            user = None
        if user is None or not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError("This reset link is invalid or has expired. Please request a new one.")

        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        validate_password(attrs["password"], user)

        attrs["user"] = user
        return attrs


class DriverDocumentSerializer(serializers.ModelSerializer):
    """A driver's own view of one of their documents (the file itself is fetched separately)."""
    label = serializers.CharField(source="get_doc_type_display", read_only=True)

    class Meta:
        model = DriverDocument
        fields = ["doc_type", "label", "original_name", "status", "review_note", "uploaded_at"]
        read_only_fields = fields


class DriverDocumentUploadSerializer(serializers.Serializer):
    doc_type = serializers.ChoiceField(choices=DocumentType.choices)
    file = serializers.FileField()

    def validate_file(self, value):
        if value.content_type not in ALLOWED_DOCUMENT_TYPES:
            raise serializers.ValidationError("Upload a PDF, or a JPEG, PNG or WebP photo.")
        if value.size > MAX_DOCUMENT_SIZE:
            raise serializers.ValidationError("The file must be under 10 MB.")
        return value

    def validate_doc_type(self, value):
        profile = self.context["profile"]
        from .driver_verification import required_documents
        if value not in required_documents(profile.nationality):
            raise serializers.ValidationError("This document isn't needed for your application.")
        return value


def document_checklist(profile):
    """The driver's checklist: every required document, uploaded or not."""
    by_type = {d.doc_type: d for d in profile.documents.all()}
    status = profile.verification_status()
    items = []
    for doc_type in status["required"]:
        doc = by_type.get(doc_type)
        items.append({
            "doc_type": doc_type,
            "label": DocumentType(doc_type).label,
            "hint": DOCUMENT_HINTS[doc_type],
            "document": DriverDocumentSerializer(doc).data if doc else None,
        })
    return {
        "nationality": profile.nationality,
        "consent_given": status["consent"],
        "old_enough": status["old_enough"],
        "complete": status["complete"],
        "is_approved": profile.is_approved,
        "rejection_reason": profile.rejection_reason if profile.rejected_at else "",
        "items": items,
    }
