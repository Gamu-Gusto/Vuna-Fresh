"""
Reusable audit log helper.

Other apps should import and call this function whenever they access
a user's personal data, rather than writing to DataAccessAuditLog directly.

Usage:
    from apps.privacy.audit import log_data_access

    log_data_access(
        accessed_user=some_user,
        accessed_by=request.user,   # pass None for system/automated access
        reason="Admin viewed order history",
    )
"""
from .models import DataAccessAuditLog


def log_data_access(accessed_user, accessed_by, reason: str) -> DataAccessAuditLog:
    """
    Write a DataAccessAuditLog entry and return it.

    Args:
        accessed_user: The User whose data was accessed.
        accessed_by:   The User who performed the access, or None for system access.
        reason:        Short human-readable description of why access occurred.
    """
    return DataAccessAuditLog.objects.create(
        user=accessed_user,
        accessed_by=accessed_by,
        reason=reason,
    )
