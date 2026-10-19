"""
Start-up checks that print in the build log (Django runs them before
`migrate`), so a misconfigured deploy is visible there.
"""
from django.conf import settings
from django.core.checks import Tags, Warning, register


@register(Tags.compatibility)
def file_storage_check(app_configs, **kwargs):
    """Warn when uploads would go to the server's disk, which Render wipes on every deploy."""
    if getattr(settings, "SERVE_MEDIA_FROM_DISK", False):
        return [Warning(
            "STORAGE_BUCKET_NAME isn't set, so product photos are saved on this server's disk and "
            "deleted on every deploy or restart.",
            hint="Add the STORAGE_* variables on the API service's Environment page (see render.yaml).",
            id="vunafresh.W001",
        )]
    warnings = []
    missing = [
        name for name, value in [
            ("STORAGE_ENDPOINT_URL", settings.AWS_S3_ENDPOINT_URL),
            ("STORAGE_ACCESS_KEY_ID", settings.AWS_ACCESS_KEY_ID),
            ("STORAGE_SECRET_ACCESS_KEY", settings.AWS_SECRET_ACCESS_KEY),
            ("STORAGE_PUBLIC_DOMAIN", settings.AWS_S3_CUSTOM_DOMAIN),
        ] if not value
    ]
    if missing:
        warnings.append(Warning(
            f"STORAGE_BUCKET_NAME is set but {', '.join(missing)} {'is' if len(missing) == 1 else 'are'} not, "
            "so uploads will fail or get unusable links.",
            id="vunafresh.W002",
        ))
    if not settings.PRIVATE_STORAGE_BUCKET_NAME:
        warnings.append(Warning(
            "STORAGE_PRIVATE_BUCKET_NAME isn't set, so proofs of payment and driver documents are kept on "
            "this server's disk and deleted on every deploy or restart.",
            id="vunafresh.W003",
        ))
    return warnings
