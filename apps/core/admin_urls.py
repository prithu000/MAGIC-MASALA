"""
apps/core/admin_urls.py
Wraps the admin site with 2FA enforcement via django-two-factor-auth.
"""

from django.conf import settings
from django.conf import settings
from django.contrib import admin
from django.urls import path
from two_factor.admin import AdminSiteOTPRequired, unpatch_admin

if settings.DEBUG:
    unpatch_admin()
else:
    admin.site.__class__ = AdminSiteOTPRequired

from django.views.generic import RedirectView
from apps.core.admin_views import admin_guide_view

urlpatterns = [
    path("guide/", admin_guide_view, name="admin_guide"),
    path("combos/customizecombOrule/", RedirectView.as_view(url="/admin/combos/customizecomborule/", permanent=False)),
    path("combos/customizecombOrule/<path:rest>/", RedirectView.as_view(url="/admin/combos/customizecomborule/%(rest)s", permanent=False)),
    path("", admin.site.urls),
]

