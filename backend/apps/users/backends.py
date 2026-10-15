"""
Django admin permissions for managers.

A manager is an admin-role, staff, non-superuser account (see
apps.users.permissions.is_super_admin). Managers can use every part of Django
admin except the super admin's two reserved powers: managing accounts (which
would let them create admins or make themselves superuser), farmer payouts and
the commission rate that decides them.
Django's groups and permissions are off-limits too, so a manager can't grant
themselves anything.
"""

# app_label.codename permissions a manager never has
RESERVED_PERMISSIONS = {
    "users.add_user", "users.change_user", "users.delete_user",
    "payments.add_farmerpayout", "payments.change_farmerpayout", "payments.delete_farmerpayout",
    "payments.add_commissionsettings", "payments.change_commissionsettings", "payments.delete_commissionsettings",
}
RESERVED_APPS = {"auth"}


def _is_manager(user):
    return bool(
        user.is_active and user.is_staff and not user.is_superuser and getattr(user, "role", None) == "admin"
    )


class ManagerPermissionBackend:
    """Grants permissions only; authentication is left to ModelBackend."""

    def authenticate(self, request, **credentials):
        return None

    def get_user(self, user_id):
        return None

    def has_perm(self, user_obj, perm, obj=None):
        if not _is_manager(user_obj):
            return False
        return perm not in RESERVED_PERMISSIONS and perm.split(".", 1)[0] not in RESERVED_APPS

    def has_module_perms(self, user_obj, app_label):
        return _is_manager(user_obj) and app_label not in RESERVED_APPS
