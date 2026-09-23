"""
config/settings/production.py
Production: PostgreSQL, S3/Cloudinary, security headers, Sentry, Redis cache.
"""

import sentry_sdk

from .base import *  # noqa: F401, F403

DEBUG = False

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASES = {
    "default": env.db("DATABASE_URL")  # noqa: F405
}
DATABASES["default"]["CONN_MAX_AGE"] = 60

# ---------------------------------------------------------------------------
# Security headers & Cookie Security
# ---------------------------------------------------------------------------
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin-allow-popups"

CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=["https://mumagicmasala.com", "https://www.mumagicmasala.com"],
)

# ---------------------------------------------------------------------------
# Media storage — S3 or Cloudinary
# ---------------------------------------------------------------------------
if env.bool("USE_S3", default=False):  # noqa: F405
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")  # noqa: F405
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")  # noqa: F405
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")  # noqa: F405
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="ap-south-1")  # noqa: F405
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = "public-read"
    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com"
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"
elif env.bool("USE_CLOUDINARY", default=False):  # noqa: F405
    import cloudinary

    cloudinary.config(
        cloud_name=env("CLOUDINARY_CLOUD_NAME"),  # noqa: F405
        api_key=env("CLOUDINARY_API_KEY"),  # noqa: F405
        api_secret=env("CLOUDINARY_API_SECRET"),  # noqa: F405
    )
    DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"
else:
    # Production VPS local media served directly by Nginx at /media/
    DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"  # noqa: F405

# ---------------------------------------------------------------------------
# Sentry
# ---------------------------------------------------------------------------
SENTRY_DSN = env("SENTRY_DSN", default="")  # noqa: F405
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=0.1,
        send_default_pii=False,
    )

# ---------------------------------------------------------------------------
# Logging (production: structured console, safe optional file handler)
# ---------------------------------------------------------------------------
log_file = env("DJANGO_LOG_FILE", default="")
if log_file:
    import os
    try:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        LOGGING["handlers"]["file"] = {  # noqa: F405
            "class": "logging.FileHandler",
            "filename": log_file,
            "formatter": "verbose",
        }
        LOGGING["loggers"]["apps.orders"]["handlers"] = ["console", "file"]  # noqa: F405
        LOGGING["loggers"]["apps.payments"]["handlers"] = ["console", "file"]  # noqa: F405
    except Exception:
        pass

