"""apps/catalog/urls.py"""

from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.ProductListView.as_view(), name="product_list"),
    path("category/<slug:slug>/", views.CategoryDetailView.as_view(), name="category_detail_alt"),
    path("<slug:slug>/", views.CategoryDetailView.as_view(), name="category_detail"),
    path(
        "<slug:category_slug>/<slug:slug>/",
        views.ProductDetailView.as_view(),
        name="product_detail",
    ),
]
