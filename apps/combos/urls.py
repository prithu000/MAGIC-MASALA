"""apps/combos/urls.py"""

from django.urls import path
from . import views

app_name = "combos"

urlpatterns = [
    path("", views.combo_list, name="combo_list"),
    path("build/", views.combo_builder, name="combo_builder"),
    path("build/save/", views.save_custom_combo, name="save_custom_combo"),
    path("<slug:slug>/", views.fixed_combo_detail, name="fixed_combo_detail"),
]
