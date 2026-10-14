from django.contrib import admin
from .models import ConsentRecord, DataAccessAuditLog, DataAccessRequest


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    list_display = ["user", "consent_type", "granted", "granted_at", "revoked_at"]
    list_filter = ["consent_type", "granted"]
    search_fields = ["user__email"]
    readonly_fields = ["granted_at", "revoked_at"]


@admin.register(DataAccessRequest)
class DataAccessRequestAdmin(admin.ModelAdmin):
    list_display = ["user", "request_type", "status", "requested_at", "completed_at"]
    list_filter = ["request_type", "status"]
    search_fields = ["user__email"]
    readonly_fields = ["requested_at"]


@admin.register(DataAccessAuditLog)
class DataAccessAuditLogAdmin(admin.ModelAdmin):
    list_display = ["user", "accessed_by", "reason", "accessed_at"]
    search_fields = ["user__email", "accessed_by__email", "reason"]
    readonly_fields = ["user", "accessed_by", "reason", "accessed_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
