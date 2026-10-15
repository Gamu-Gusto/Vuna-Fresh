from django.conf import settings
from django.db import models
from django.utils import timezone


class ConsentType(models.TextChoices):
    DATA_COLLECTION = "data_collection", "Data Collection"
    MARKETING = "marketing", "Marketing"
    COOKIES = "cookies", "Cookies"
    THIRD_PARTY_SHARING = "third_party_sharing", "Third-Party Sharing"
    # Drivers: collecting and checking ID, licence, vehicle, address and bank documents
    DRIVER_VERIFICATION = "driver_verification", "Driver Verification Documents"


class DataAccessRequestType(models.TextChoices):
    ACCESS = "access", "Access"
    DELETION = "deletion", "Deletion"
    PORTABILITY = "portability", "Portability"


class DataAccessRequestStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    DENIED = "denied", "Denied"


class ConsentRecord(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="consent_records",
    )
    consent_type = models.CharField(max_length=20, choices=ConsentType.choices)
    granted = models.BooleanField(default=False)
    granted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "consent_records"
        # One record per user per consent type — upsert pattern used in the view
        unique_together = [("user", "consent_type")]
        ordering = ["consent_type"]

    def __str__(self):
        state = "granted" if self.granted else "revoked"
        return f"ConsentRecord({self.user.email}, {self.consent_type}, {state})"

    def grant(self):
        self.granted = True
        self.granted_at = timezone.now()
        self.revoked_at = None
        self.save(update_fields=["granted", "granted_at", "revoked_at"])

    def revoke(self):
        self.granted = False
        self.revoked_at = timezone.now()
        self.save(update_fields=["granted", "revoked_at"])


class DataAccessRequest(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="data_access_requests",
    )
    request_type = models.CharField(max_length=12, choices=DataAccessRequestType.choices)
    status = models.CharField(
        max_length=10,
        choices=DataAccessRequestStatus.choices,
        default=DataAccessRequestStatus.PENDING,
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "data_access_requests"
        ordering = ["-requested_at"]

    def __str__(self):
        return f"DataAccessRequest({self.user.email}, {self.request_type}, {self.status})"


class DataAccessAuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="data_access_audit_logs",
    )
    accessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="data_accesses_performed",
    )
    reason = models.CharField(max_length=255)
    accessed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "data_access_audit_logs"
        ordering = ["-accessed_at"]

    def __str__(self):
        by = self.accessed_by.email if self.accessed_by else "system"
        return f"DataAccessAuditLog(user={self.user.email}, by={by})"
