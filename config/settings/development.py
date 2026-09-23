"""
config/settings/development.py
Local development: SQLite, console email, debug toolbar, no HTTPS enforcement.
"""

from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Use local file system for media in development
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

# Email backend (respects .env EMAIL_BACKEND, fallback to console if not specified)
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")

# Django Debug Toolbar
INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405
INTERNAL_IPS = ["127.0.0.1"]

# Cache — in-memory cache for local dev without external Redis requirement
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "mu-magic-masala-dev-cache",
    }
}

# Sessions — use database backend in development
SESSION_ENGINE = "django.contrib.sessions.backends.db"

# Relax password rules in dev
AUTH_PASSWORD_VALIDATORS = []  # noqa: F405

# Run Celery tasks eagerly in dev so workers are not strictly required locally
CELERY_TASK_ALWAYS_EAGER = True

# In dev, direct login to standard admin login
LOGIN_URL = "admin:login"

# Allow payment gateway simulation in dev when Razorpay test keys aren't set
# This lets the full order flow be tested without real Razorpay credentials
ALLOW_DEV_PAYMENT_SIMULATION = True
