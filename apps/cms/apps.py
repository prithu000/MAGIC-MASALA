"""apps/cms/apps.py"""
from django.apps import AppConfig

class CMSConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cms"
    verbose_name = "Homepage Content"
