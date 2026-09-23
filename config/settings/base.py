"""
config/settings/base.py
Shared settings for all environments.
"""

import os
from pathlib import Path

import environ

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django.contrib.humanize",
]

THIRD_PARTY_APPS = [
    "solo",
    "imagekit",
    "ckeditor",
    "ckeditor_uploader",
    "storages",
    "celery",
    "django_celery_beat",
    "django_celery_results",
    "axes",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
    "two_factor",
    "widget_tweaks",
]

LOCAL_APPS = [
    "apps.core",
    "apps.catalog",
    "apps.accounts",
    "apps.cart",
    "apps.orders",
    "apps.payments",
    "apps.combos",
    "apps.coupons",
    "apps.cms",
    "apps.reviews",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.core.middleware.SecurityHeadersMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site_settings",
                "apps.core.context_processors.cart_context",
                "apps.core.context_processors.google_auth_context",
                "apps.cms.context_processors.announcement_bar",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "auth.User"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "apps.accounts.backends.EmailOrUsernameModelBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

LOGIN_URL = "two_factor:login"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & Media (base — overridden per env)
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="MU Magic Masala <hello@mumagicmasala.com>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# ---------------------------------------------------------------------------
# Redis & Celery
# ---------------------------------------------------------------------------
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "default"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# ---------------------------------------------------------------------------
# Razorpay
# ---------------------------------------------------------------------------
RAZORPAY_KEY_ID = env("RAZORPAY_KEY_ID", default="")
RAZORPAY_KEY_SECRET = env("RAZORPAY_KEY_SECRET", default="")
RAZORPAY_WEBHOOK_SECRET = env("RAZORPAY_WEBHOOK_SECRET", default="")

# ---------------------------------------------------------------------------
# Google OAuth 2.0
# ---------------------------------------------------------------------------
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID", default="")
GOOGLE_CLIENT_SECRET = env("GOOGLE_CLIENT_SECRET", default="")
GOOGLE_REDIRECT_URI = env("GOOGLE_REDIRECT_URI", default="")

# ---------------------------------------------------------------------------
# CKEditor
# ---------------------------------------------------------------------------
CKEDITOR_UPLOAD_PATH = "ckeditor_uploads/"
CKEDITOR_RESTRICT_BY_USER = True
CKEDITOR_CONFIGS = {
    "default": {
        "toolbar": "Custom",
        "toolbar_Custom": [
            ["Bold", "Italic", "Underline", "Strike"],
            ["NumberedList", "BulletedList", "-", "Outdent", "Indent"],
            ["Link", "Unlink"],
            ["Image", "Table", "HorizontalRule"],
            ["Source"],
            ["Styles", "Format", "Font", "FontSize"],
        ],
        "height": 300,
        "width": "100%",
        "removePlugins": "exportpdf",
    },
}

# ---------------------------------------------------------------------------
# Django Axes (brute-force protection)
# ---------------------------------------------------------------------------
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # 1 hour lockout
AXES_LOCKOUT_PARAMETERS = ["ip_address", "username"]
AXES_RESET_ON_SUCCESS = True

# ---------------------------------------------------------------------------
# OTP / 2FA
# ---------------------------------------------------------------------------
OTP_TOTP_ISSUER = env("OTP_TOTP_ISSUER", default="MU Magic Masala Admin")
TWO_FACTOR_PATCH_ADMIN = True

# ---------------------------------------------------------------------------
# Imagekit
# ---------------------------------------------------------------------------
IMAGEKIT_DEFAULT_CACHEFILE_STRATEGY = "imagekit.cachefiles.strategies.Optimistic"

# ---------------------------------------------------------------------------
# Django Unfold Admin theme
# ---------------------------------------------------------------------------
UNFOLD = {
    "SITE_TITLE": "MU Magic Masala",
    "SITE_HEADER": "MU Magic Masala Admin",
    "SITE_SUBHEADER": "Store Management",
    "SITE_URL": "/",
    "SITE_LOGO": {
        "light": lambda request: "/static/images/logo.svg",
        "dark": lambda request: "/static/images/logo-white.svg",
    },
    "SITE_ICON": {
        "light": lambda request: "/static/images/favicon.svg",
        "dark": lambda request: "/static/images/favicon.svg",
    },
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "sizes": "32x32",
            "type": "image/svg+xml",
            "href": lambda request: "/static/images/favicon.svg",
        },
    ],
    "COLORS": {
        "primary": {
            "50": "254 242 242",
            "100": "254 226 226",
            "200": "254 202 202",
            "300": "252 165 165",
            "400": "248 113 113",
            "500": "180 35 35",    # deep masala red
            "600": "153 27 27",
            "700": "127 29 29",
            "800": "95 26 26",
            "900": "75 26 26",
            "950": "47 18 18",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Store Guide & Help",
                "separator": False,
                "collapsible": False,
                "items": [
                    {"title": "📘 Store Owner Manual (गाइड)", "icon": "menu_book", "link": "/admin/guide/"},
                    {"title": "🌐 View Live Website", "icon": "open_in_new", "link": "/"},
                ],
            },
            {
                "title": "Products",
                "separator": True,
                "collapsible": True,
                "items": [
                    {"title": "All Products", "icon": "inventory_2", "link": "/admin/catalog/product/"},
                    {"title": "Categories", "icon": "category", "link": "/admin/catalog/category/"},
                    {"title": "Tags", "icon": "label", "link": "/admin/catalog/tag/"},
                ],
            },
            {
                "title": "Combos",
                "separator": False,
                "collapsible": True,
                "items": [
                    {"title": "Fixed Combos", "icon": "inventory", "link": "/admin/combos/fixedcombo/"},
                    {"title": "Build-Your-Own Combo Settings", "icon": "tune", "link": "/admin/combos/customizecomborule/"},
                    {"title": "Combo Eligible Products", "icon": "check_box", "link": "/admin/combos/customizecomboeligibleproduct/"},
                ],
            },
            {
                "title": "Orders",
                "separator": True,
                "collapsible": True,
                "items": [
                    {"title": "All Orders", "icon": "shopping_bag", "link": "/admin/orders/order/"},
                    {"title": "🛒 Customer Carts", "icon": "shopping_cart", "link": "/admin/cart/cart/"},
                    {"title": "Order Status History", "icon": "timeline", "link": "/admin/orders/orderstatushistory/"},
                ],
            },
            {
                "title": "Customers & Users",
                "separator": False,
                "collapsible": True,
                "items": [
                    {"title": "All Users", "icon": "person", "link": "/admin/auth/user/"},
                    {"title": "Customer Profiles", "icon": "people", "link": "/admin/accounts/customerprofile/"},
                    {"title": "Addresses", "icon": "location_on", "link": "/admin/accounts/address/"},
                    {"title": "Wishlists", "icon": "favorite", "link": "/admin/accounts/wishlist/"},
                ],
            },
            {
                "title": "Homepage Content",
                "separator": True,
                "collapsible": True,
                "items": [
                    {"title": "Hero Slides", "icon": "slideshow", "link": "/admin/cms/heroslide/"},
                    {"title": "Announcement Bar", "icon": "campaign", "link": "/admin/cms/announcementbar/"},
                    {"title": "Influencer Reels (Insta & YT)", "icon": "smart_display", "link": "/admin/cms/influencerreel/"},
                    {"title": "Banners", "icon": "image", "link": "/admin/cms/banner/"},
                    {"title": "Testimonials", "icon": "rate_review", "link": "/admin/cms/testimonial/"},
                ],
            },
            {
                "title": "Content & Pages",
                "separator": False,
                "collapsible": True,
                "items": [
                    {"title": "Static Pages", "icon": "article", "link": "/admin/cms/staticpage/"},
                    {"title": "Blog & Recipes", "icon": "menu_book", "link": "/admin/cms/blogpost/"},
                    {"title": "FAQs", "icon": "help", "link": "/admin/cms/faqitem/"},
                ],
            },
            {
                "title": "Marketing & Emails",
                "separator": True,
                "collapsible": True,
                "items": [
                    {"title": "📧 Email Settings & Brevo", "icon": "settings_suggest", "link": "/admin/core/emailsettings/1/change/"},
                    {"title": "🚀 Email Campaigns & Offers", "icon": "campaign", "link": "/admin/core/emailcampaign/"},
                    {"title": "📋 Email Delivery Logs", "icon": "mark_email_read", "link": "/admin/core/emaillog/"},
                    {"title": "Coupons", "icon": "local_offer", "link": "/admin/coupons/coupon/"},
                    {"title": "Coupon Usage", "icon": "bar_chart", "link": "/admin/coupons/couponusage/"},
                ],
            },
            {
                "title": "Reviews",
                "separator": False,
                "collapsible": True,
                "items": [
                    {"title": "Pending Approval", "icon": "pending_actions", "link": "/admin/reviews/productreview/?is_approved__exact=0"},
                    {"title": "All Reviews", "icon": "star", "link": "/admin/reviews/productreview/"},
                ],
            },
            {
                "title": "Settings",
                "separator": True,
                "collapsible": True,
                "items": [
                    {"title": "Site Settings", "icon": "settings", "link": "/admin/core/sitesettings/1/change/"},
                    {"title": "Scheduled Tasks", "icon": "schedule", "link": "/admin/django_celery_beat/periodictask/"},
                ],
            },
        ],
    },
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {asctime} {module} {process:d} {thread:d} — {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO"},
        "apps.orders": {"handlers": ["console"], "level": "DEBUG", "propagate": True},
        "apps.payments": {"handlers": ["console"], "level": "DEBUG", "propagate": True},
    },
}
