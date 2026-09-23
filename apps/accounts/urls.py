"""apps/accounts/urls.py"""

from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("register/", views.register, name="register"),
    path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("orders/", views.order_list, name="order_list"),
    path("orders/<str:order_number>/", views.order_detail, name="order_detail"),
    path("addresses/", views.address_list, name="address_list"),
    path("addresses/add/", views.address_create, name="address_create"),
    path("addresses/<int:pk>/edit/", views.address_edit, name="address_edit"),
    path("addresses/<int:pk>/delete/", views.address_delete, name="address_delete"),
    path("addresses/<int:pk>/set-default/", views.address_set_default, name="address_set_default"),
    path("wishlist/", views.wishlist, name="wishlist"),
    path("wishlist/toggle/<int:product_id>/", views.wishlist_toggle, name="wishlist_toggle"),
    path("profile/", views.profile_edit, name="profile_edit"),
    path("password-change/", views.CustomPasswordChangeView.as_view(), name="password_change"),
    path("password-change/done/", auth_views.PasswordChangeDoneView.as_view(
        template_name="accounts/password_change_done.html",
    ), name="password_change_done"),
    path("password-reset/", views.CustomPasswordResetView.as_view(), name="password_reset"),
    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(
        template_name="accounts/password_reset_done.html",
    ), name="password_reset_done"),
    path("password-reset-confirm/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="accounts/password_reset_confirm.html",
        success_url="/account/password-reset-complete/",
    ), name="password_reset_confirm"),
    path("password-reset-complete/", auth_views.PasswordResetCompleteView.as_view(
        template_name="accounts/password_reset_complete.html",
    ), name="password_reset_complete"),
    # Google OAuth 2.0
    path("google/login/", views.google_login, name="google_login"),
    path("google/callback/", views.google_callback, name="google_callback"),
    path("google/credential/", views.google_credential, name="google_credential"),
]
