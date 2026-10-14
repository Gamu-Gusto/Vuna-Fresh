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
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])  # noqa: F405

# Security headers
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Use Cloudflare R2 for media files in production
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
