import logging
import os
import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

from config.private_storage import private_storage

from .driver_verification import (
    MINIMUM_DRIVER_AGE, DocumentType, Nationality, age_on, required_documents,
)


class UserRole(models.TextChoices):
    CUSTOMER = "customer", "Customer"
    FARMER = "farmer", "Farmer"
    DRIVER = "driver", "Driver"
    ADMIN = "admin", "Admin"


class UserStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    DEACTIVATED = "deactivated", "Deactivated"


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", UserRole.ADMIN)
        extra_fields.setdefault("status", UserStatus.ACTIVE)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    role = models.CharField(max_length=10, choices=UserRole.choices, default=UserRole.CUSTOMER)
    status = models.CharField(max_length=12, choices=UserStatus.choices, default=UserStatus.PENDING)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        db_table = "users"
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.email} ({self.role})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(max_length=50, blank=True, help_text="e.g. Home, Work")
    street_address = models.CharField(max_length=255)
    suburb = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10)
    country = models.CharField(max_length=100, default="South Africa")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "addresses"
        ordering = ["-is_default", "-created_at"]
        verbose_name_plural = "addresses"

    def __str__(self):
        return f"{self.street_address}, {self.city} ({self.user.email})"

    def save(self, *args, **kwargs):
        # Enforce only one default address per user
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(
                is_default=False
            )
        super().save(*args, **kwargs)


class BuyerType(models.TextChoices):
    INDIVIDUAL = "individual", "Individual"
    BUSINESS = "business", "Business"


class BuyerProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="buyer_profile",
        limit_choices_to={"role": UserRole.CUSTOMER},
    )
    buyer_type = models.CharField(max_length=10, choices=BuyerType.choices, default=BuyerType.INDIVIDUAL)
    preferred_delivery_address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "buyer_profiles"

    def __str__(self):
        return f"BuyerProfile({self.user.email})"


class FarmerProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="farmer_profile",
        limit_choices_to={"role": UserRole.FARMER},
    )
    farm_name = models.CharField(max_length=255)
    farm_description = models.TextField(blank=True)
    farm_location = models.CharField(max_length=255, blank=True)
    is_approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="approved_farmers",
    )
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "farmer_profiles"

    def __str__(self):
        return f"FarmerProfile({self.farm_name})"


class DriverProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="driver_profile",
        limit_choices_to={"role": UserRole.DRIVER},
    )
    vehicle_type = models.CharField(max_length=100, blank=True)
    vehicle_registration = models.CharField(max_length=20, blank=True)
    is_approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="approved_drivers",
    )
    rejection_reason = models.TextField(blank=True)
    # When the application was rejected: its documents are deleted 30 days later
    rejected_at = models.DateTimeField(null=True, blank=True)
    is_available = models.BooleanField(default=False)

    # Identity, collected at signup (see driver_verification.py). Drivers must be 21+.
    date_of_birth = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=20, choices=Nationality.choices, blank=True)
    id_number = models.CharField(max_length=13, blank=True, help_text="South African citizens")
    passport_number = models.CharField(max_length=20, blank=True, help_text="Foreign nationals")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "driver_profiles"

    def __str__(self):
        return f"DriverProfile({self.user.email})"

    @property
    def age(self):
        return age_on(self.date_of_birth) if self.date_of_birth else None

    def verification_status(self):
        """
        {"required": [...], "missing": [...], "rejected": [...], "consent": bool,
         "old_enough": bool, "complete": bool} — complete means an admin may approve.
        """
        from apps.privacy.models import ConsentRecord, ConsentType

        required = required_documents(self.nationality)
        by_type = {d.doc_type: d for d in self.documents.all()}
        missing = [t for t in required if t not in by_type]
        rejected = [t for t in required if t in by_type and by_type[t].status == DocumentStatus.REJECTED]
        consent = ConsentRecord.objects.filter(
            user_id=self.user_id, consent_type=ConsentType.DRIVER_VERIFICATION, granted=True,
        ).exists()
        old_enough = self.age is not None and self.age >= MINIMUM_DRIVER_AGE
        return {
            "required": list(required), "missing": missing, "rejected": rejected,
            "consent": consent, "old_enough": old_enough,
            "complete": bool(required) and not missing and not rejected and consent and old_enough,
        }


class DocumentStatus(models.TextChoices):
    SUBMITTED = "submitted", "Waiting to be checked"
    ACCEPTED = "accepted", "Accepted"
    REJECTED = "rejected", "Needs a new upload"


def driver_document_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower() or ".pdf"
    return f"driver-documents/{uuid.uuid4()}{ext}"


class DriverDocument(models.Model):
    """
    One verification document (see driver_verification.DocumentType). Stored in
    private storage: never publicly linked, viewed by admins through the API
    with each view written to the privacy audit log. A new upload of the same
    type replaces the old one.
    """
    driver = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField(max_length=30, choices=DocumentType.choices)
    file = models.FileField(storage=private_storage, upload_to=driver_document_path)
    original_name = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=10, choices=DocumentStatus.choices, default=DocumentStatus.SUBMITTED)
    review_note = models.CharField(max_length=255, blank=True, help_text="Shown to the driver if rejected")
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_driver_documents",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "driver_documents"
        ordering = ["doc_type"]
        constraints = [
            models.UniqueConstraint(fields=["driver", "doc_type"], name="one_document_per_type_per_driver"),
        ]

    def __str__(self):
        return f"DriverDocument({self.driver_id}, {self.doc_type}, {self.status})"


@receiver(post_delete, sender=DriverDocument)
def delete_driver_document_file(sender, instance, **kwargs):
    # Rows go when a document is replaced, purged after 30 days or the account is
    # deleted: the file must go with them, not linger in storage.
    if instance.file:
        try:
            instance.file.delete(save=False)
        except Exception:  # the row is gone either way; don't fail the request over the file
            logging.getLogger(__name__).exception("Could not delete driver document file %s", instance.file.name)
