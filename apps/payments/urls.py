"""apps/payments/urls.py"""
from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("checkout/<int:order_id>/", views.razorpay_checkout, name="razorpay_checkout"),
    path("webhook/razorpay/", views.razorpay_webhook, name="razorpay_webhook"),
]
