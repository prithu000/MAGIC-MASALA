"""apps/catalog/search_urls.py"""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.search_view, name="search"),
]
