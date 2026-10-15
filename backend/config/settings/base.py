"""
Base settings shared across all environments.
All secrets MUST come from environment variables — never hardcode them here.
"""
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)

# Read .env file if present (development convenience only)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
]

LOCAL_APPS = [
    "apps.users",
    "apps.products",
    "apps.orders",
    "apps.privacy",
    "apps.reviews",
    "apps.issues",
    "apps.subscriptions",
    "apps.notifications",
    "apps.buyers",
    "apps.payments",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database — always read from DATABASE_URL env var
DATABASES = {
    "default": env.db("DATABASE_URL"),
}

# Custom user model
AUTH_USER_MODEL = "users.User"
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    # Managers get Django admin access minus the super admin's reserved powers
    "apps.users.backends.ManagerPermissionBackend",
]

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Johannesburg"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# X-Buyer-Account lets a business account member act on behalf of the shared
# account (see apps.buyers.resolvers) instead of their own individual profile —
# needs to be explicitly allowed or the browser strips it on cross-origin requests.
from corsheaders.defaults import default_headers as _cors_default_headers  # noqa: E402

CORS_ALLOW_HEADERS = list(_cors_default_headers) + ["x-buyer-account"]

# ── Django REST Framework ──────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.NamespaceVersioning",
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ["v1"],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "EXCEPTION_HANDLER": "config.exceptions.custom_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    # Only views that opt in with throttle_scope are throttled.
    "DEFAULT_THROTTLE_RATES": {
        "password_reset": "10/hour",
    },
}

# ── Simple JWT ────────────────────────────────────────────────────────────────
from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ── File/image storage (any S3-compatible service) ──────────────────────────
# Product photos and proofs of payment. Works with Supabase Storage, Cloudflare
# R2, Backblaze B2 and the like. The older R2_* names are still read as a
# fallback. Without a bucket, production stores files on the server's own disk.
def _storage_env(name, default=""):
    return env(f"STORAGE_{name}", default="") or env(f"R2_{name}", default=default)


AWS_ACCESS_KEY_ID = _storage_env("ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = _storage_env("SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = _storage_env("BUCKET_NAME")
AWS_S3_ENDPOINT_URL = _storage_env("ENDPOINT_URL")
# R2 uses "auto"; Supabase needs the project's region (e.g. eu-central-1)
AWS_S3_REGION_NAME = _storage_env("REGION", default="auto")
# Supabase needs path-style addresses (endpoint/bucket/key); R2 works either way
AWS_S3_ADDRESSING_STYLE = _storage_env("ADDRESSING_STYLE") or None
# Access is set on the bucket (public bucket / public domain), not per object
AWS_DEFAULT_ACL = None
AWS_S3_FILE_OVERWRITE = False
# Stored URLs (Product.image_url, DirectDepositProof.file_url) must be permanent and
# short, so serve from the bucket's public address instead of expiring signed URLs.
# Supabase: <project-ref>.supabase.co/storage/v1/object/public/<bucket> (no https://)
AWS_S3_CUSTOM_DOMAIN = _storage_env("PUBLIC_DOMAIN") or None
AWS_QUERYSTRING_AUTH = AWS_S3_CUSTOM_DOMAIN is None

# Sensitive uploads (proofs of payment, driver documents) go to a separate
# PRIVATE bucket on the same account, never the public one: see
# config/private_storage.py. Without it they're kept on local disk, unserved.
PRIVATE_STORAGE_BUCKET_NAME = env("STORAGE_PRIVATE_BUCKET_NAME", default="")
PRIVATE_MEDIA_ROOT = BASE_DIR / "private_media"

# ── PayFast ───────────────────────────────────────────────────────────────────
# Credentials never touch the frontend — the backend builds the signed redirect
# form fields server-side and hands the frontend only process_url + fields.
# Off until the PayFast merchant account is live — checkout is EFT/direct deposit only.
PAYFAST_ENABLED = env.bool("PAYFAST_ENABLED", default=False)
PAYFAST_MERCHANT_ID = env("PAYFAST_MERCHANT_ID", default="")
PAYFAST_MERCHANT_KEY = env("PAYFAST_MERCHANT_KEY", default="")
PAYFAST_PASSPHRASE = env("PAYFAST_PASSPHRASE", default="")
PAYFAST_SANDBOX = env.bool("PAYFAST_SANDBOX", default=True)
PAYFAST_NOTIFY_URL = env("PAYFAST_NOTIFY_URL", default="")
PAYFAST_RETURN_URL = env("PAYFAST_RETURN_URL", default="")
PAYFAST_CANCEL_URL = env("PAYFAST_CANCEL_URL", default="")

# ── Direct deposit (platform bank account shown to buyers) ───────────────────
PLATFORM_BANK_NAME = env("PLATFORM_BANK_NAME", default="")
PLATFORM_BANK_ACCOUNT_HOLDER = env("PLATFORM_BANK_ACCOUNT_HOLDER", default="")
PLATFORM_BANK_ACCOUNT_NUMBER = env("PLATFORM_BANK_ACCOUNT_NUMBER", default="")
PLATFORM_BANK_BRANCH_CODE = env("PLATFORM_BANK_BRANCH_CODE", default="")
PLATFORM_BANK_ACCOUNT_TYPE = env("PLATFORM_BANK_ACCOUNT_TYPE", default="")

# ── Email ─────────────────────────────────────────────────────────────────────
# Any SMTP provider works (Brevo, Gmail app password, Zoho, etc.). With no
# EMAIL_HOST set, emails are printed to the console instead of sent.
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_TIMEOUT = 10
EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend" if EMAIL_HOST
    else "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Vuna Fresh <no-reply@vunafresh.co.za>")

# Public URL of the Next.js web app — used for links in emails (password reset, orders).
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000").rstrip("/")
