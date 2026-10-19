"""Production settings."""
from .base import *  # noqa: F401, F403

DEBUG = False

# Render sets RENDER_EXTERNAL_HOSTNAME to the service's public *.onrender.com host
_render_host = env("RENDER_EXTERNAL_HOSTNAME", default="")  # noqa: F405
if _render_host:
    ALLOWED_HOSTS = [*ALLOWED_HOSTS, _render_host]  # noqa: F405

# The web frontend runs on a different origin, so it must be allowed explicitly,
# e.g. CORS_ALLOWED_ORIGINS=https://vunafresh-web.onrender.com
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])  # noqa: F405
# Pattern alternative, for hosts that add random suffixes to service names
# (Render: vunafresh-web-8mmw, vunafresh-web-20qr, ...). Separate several with commas.
CORS_ALLOWED_ORIGIN_REGEXES = env.list("CORS_ALLOWED_ORIGIN_REGEXES", default=[])  # noqa: F405
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])  # noqa: F405

# Security headers
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Uploaded files (product photos, proof of payment). An S3-compatible bucket
# (Supabase Storage) when STORAGE_BUCKET_NAME is set; otherwise the server's own
# disk, which Render wipes on every deploy and restart.
SERVE_MEDIA_FROM_DISK = not AWS_STORAGE_BUCKET_NAME  # noqa: F405
if SERVE_MEDIA_FROM_DISK:
    DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"  # noqa: F405
else:
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

# Prints a warning in the build log if file storage isn't set up (see config/checks.py)
import config.checks  # noqa: E402, F401
