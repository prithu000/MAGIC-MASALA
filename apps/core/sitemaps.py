"""
apps/core/sitemaps.py — sitemap classes for all public content.
"""

from django.contrib.sitemaps import Sitemap

from apps.catalog.models import Category, Product
from apps.cms.models import BlogPost, StaticPage


class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Product.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return obj.get_absolute_url()


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Category.objects.filter(is_active=True)

    def location(self, obj):
        return obj.get_absolute_url()


class BlogPostSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return BlogPost.objects.filter(published_at__isnull=False).order_by("-published_at")

    def lastmod(self, obj):
        return obj.published_at

    def location(self, obj):
        return obj.get_absolute_url()


class StaticPageSitemap(Sitemap):
    changefreq = "yearly"
    priority = 0.5

    def items(self):
        return StaticPage.objects.all()

    def location(self, obj):
        return obj.get_absolute_url()
