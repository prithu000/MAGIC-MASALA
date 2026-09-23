"""apps/orders/urls.py"""

from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    path("", views.checkout_address, name="checkout"),
    path("address/", views.checkout_address, name="checkout_address"),
    path("payment/", views.checkout_payment, name="checkout_payment"),
    path("create/", views.create_order, name="create_order"),
    path("confirm/<str:order_number>/", views.order_confirmation, name="confirmation"),
    path("confirmation/<str:order_number>/", views.order_confirmation, name="order_confirmation"),
    path("pincode-lookup/<str:pincode>/", views.pincode_lookup, name="pincode_lookup"),
]
