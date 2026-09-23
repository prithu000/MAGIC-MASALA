"""
apps/core/context_processors.py
Injects SiteSettings and cart count into every template context.
"""

from .models import SiteSettings


def site_settings(request):
    """Make SiteSettings available as `settings` in every template."""
    return {"site_settings": SiteSettings.get_solo()}


def cart_context(request):
    """Inject cart item count for the sticky cart icon in the navbar."""
    from apps.cart.services import CartService

    cart = CartService.get_or_create_cart(request)
    return {
        "cart_item_count": cart.items.count() if cart else 0,
    }


def google_auth_context(request):
    """Inject Google OAuth Client ID into templates."""
    from apps.accounts.google_auth import get_google_credentials, is_google_auth_configured

    client_id, _ = get_google_credentials()
    return {
        "google_client_id": client_id,
        "is_google_auth_configured": is_google_auth_configured(),
    }
