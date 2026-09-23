"""config/urls.py — root URL configuration."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.generic import TemplateView
import two_factor.urls

from apps.accounts.views import google_login, google_callback
from apps.core.sitemaps import (
    BlogPostSitemap,
    CategorySitemap,
    ProductSitemap,
    StaticPageSitemap,
)

sitemaps = {
    "products": ProductSitemap,
    "categories": CategorySitemap,
    "blog": BlogPostSitemap,
    "pages": StaticPageSitemap,
}

urlpatterns = [
    # Admin (2FA-wrapped)
    path("admin/", include("apps.core.admin_urls")),

    # App URLs
    path("account/", include("apps.accounts.urls")),

    # ─── Google OAuth URL aliases ────────────────────────────────────────────
    # The CANONICAL callback is /account/google/callback/ (inside accounts.urls).
    # All aliases below redirect to the same google_callback view so that
    # ANY redirect URI registered in Google Cloud Console will work.
    path("accounts/google/login/", google_login),
    # Most common aliases registered in Google Cloud Console:
    path("accounts/google/login/callback/", google_callback),   # ← currently in Google Console
    path("accounts/google/callback/", google_callback),
    path("account/google/login/callback/", google_callback),
    # ────────────────────────────────────────────────────────────────────────

    path("shop/", include("apps.catalog.urls")),
    path("combos/", include("apps.combos.urls")),
    path("cart/", include("apps.cart.urls")),
    path("checkout/", include("apps.orders.urls")),
    path("payments/", include("apps.payments.urls")),

    # Auth / 2FA
    path("", include(two_factor.urls.urlpatterns)),
    path("reviews/", include("apps.reviews.urls")),
    path("search/", include("apps.catalog.search_urls")),
    path("api/pincode/<str:pincode>/", include([
        path("", __import__("apps.orders.views", fromlist=["pincode_lookup"]).pincode_lookup, name="api_pincode"),
    ])),
    path("", include("apps.cms.urls")),

    # SEO
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),

    # CKEditor media uploads (Strictly restricted to authenticated staff members)
    path(
        "ckeditor/upload/",
        __import__("django.contrib.admin.views.decorators", fromlist=["staff_member_required"]).staff_member_required(
            __import__("ckeditor_uploader.views", fromlist=["upload"]).upload
        ),
        name="ckeditor_upload",
    ),
    path(
        "ckeditor/browse/",
        __import__("django.contrib.admin.views.decorators", fromlist=["staff_member_required"]).staff_member_required(
            __import__("ckeditor_uploader.views", fromlist=["browse"]).browse
        ),
        name="ckeditor_browse",
    ),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
