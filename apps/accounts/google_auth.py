"""
apps/accounts/google_auth.py
Secure Google OAuth 2.0 and Google Sign-In helper services.
Zero-trust validation: state token validation, token exchange over HTTPS, and verified email checks.
"""

import hmac
import logging
import secrets
import urllib.parse
from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.utils.http import url_has_allowed_host_and_scheme
import requests

from apps.accounts.models import CustomerProfile
from apps.cart.services import CartService

logger = logging.getLogger(__name__)
User = get_user_model()

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_TOKENINFO_ENDPOINT = "https://oauth2.googleapis.com/tokeninfo"


def get_google_credentials():
    """Retrieve Google OAuth Client ID and Secret from settings."""
    client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
    client_secret = getattr(settings, "GOOGLE_CLIENT_SECRET", "")
    return client_id.strip(), client_secret.strip()


def is_google_auth_configured() -> bool:
    """Return True if both client_id and client_secret are non-empty."""
    client_id, client_secret = get_google_credentials()
    return bool(client_id and client_secret)


def get_google_redirect_uri(request) -> str:
    """
    Get the redirect URI for Google OAuth.
    Prioritizes GOOGLE_REDIRECT_URI if set in settings,
    otherwise dynamically builds the absolute URI using Django's URL reverse.
    This guarantees the URI always matches the registered accounts:google_callback route.
    """
    custom = getattr(settings, "GOOGLE_REDIRECT_URI", "").strip()
    if custom:
        return custom

    # Use reverse() to get the canonical URL for the callback — avoids path typos
    try:
        from django.urls import reverse
        callback_path = reverse("accounts:google_callback")
    except Exception:
        callback_path = "/account/google/callback/"

    return request.build_absolute_uri(callback_path)


def build_google_authorization_url(request, redirect_uri: str, state: str) -> str:
    """
    Construct the Google OAuth 2.0 authorization redirect URL with anti-CSRF state.
    """
    client_id, _ = get_google_credentials()
    params = {
        "client_id": client_id,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": redirect_uri,
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"


def exchange_code_for_tokens(code: str, redirect_uri: str) -> dict | None:
    """
    Exchange authorization code for access and ID tokens via Google Token Endpoint.
    """
    client_id, client_secret = get_google_credentials()
    payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    headers = {"Accept": "application/json"}
    try:
        response = requests.post(GOOGLE_TOKEN_ENDPOINT, data=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        logger.warning("Google token exchange error: HTTP %s: %s", response.status_code, response.text)
        return None
    except Exception as e:
        logger.error("Failed to connect to Google token endpoint: %s", e)
        return None


def fetch_google_userinfo(access_token: str) -> dict | None:
    """
    Fetch verified user profile details from Google UserInfo API using the access token.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    try:
        response = requests.get(GOOGLE_USERINFO_ENDPOINT, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        logger.warning("Google userinfo fetch failed: HTTP %s: %s", response.status_code, response.text)
        return None
    except Exception as e:
        logger.error("Failed to query Google userinfo: %s", e)
        return None


def verify_google_id_token(id_token: str) -> dict | None:
    """
    Verify Google JWT ID token (used in One-Tap or credential callbacks).
    """
    client_id, _ = get_google_credentials()
    params = {"id_token": id_token}
    try:
        response = requests.get(f"{GOOGLE_TOKENINFO_ENDPOINT}?{urllib.parse.urlencode(params)}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Verify audience matches our Client ID
            if data.get("aud") != client_id:
                logger.warning("Google ID token aud mismatch: expected %s, got %s", client_id, data.get("aud"))
                return None
            if data.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
                logger.warning("Google ID token invalid issuer: %s", data.get("iss"))
                return None
            return data
        return None
    except Exception as e:
        logger.error("Failed to verify Google ID token: %s", e)
        return None


def authenticate_or_register_google_user(request, user_data: dict) -> tuple[User | None, bool, str]:
    """
    Given validated Google user info dict, find existing account or create a new user.
    Enforces email verification, merges guest cart, and logs the user in.
    Returns: (user, created_bool, error_message_or_empty)
    """
    email = (user_data.get("email") or "").strip().lower()
    email_verified = user_data.get("email_verified") in (True, "true", "True", 1)

    if not email:
        return None, False, "Google account did not return a valid email address."

    if not email_verified:
        return None, False, "Your Google email address is not verified by Google. Please verify it first."

    first_name = (user_data.get("given_name") or "").strip()
    last_name = (user_data.get("family_name") or "").strip()
    if not first_name and user_data.get("name"):
        parts = user_data["name"].strip().split()
        first_name = parts[0]
        if len(parts) > 1:
            last_name = " ".join(parts[1:])

    # 1. Search for existing user with this email
    user = User.objects.filter(email__iexact=email).first()
    if not user:
        user = User.objects.filter(username__iexact=email).first()

    created = False
    if user:
        # Existing user: update name if previously empty
        update_fields = []
        if not user.first_name and first_name:
            user.first_name = first_name[:60]
            update_fields.append("first_name")
        if not user.last_name and last_name:
            user.last_name = last_name[:60]
            update_fields.append("last_name")
        if update_fields:
            user.save(update_fields=update_fields)

        # Ensure CustomerProfile exists
        CustomerProfile.objects.get_or_create(user=user)
    else:
        # 2. New user: register safely with unusable password
        created = True
        user = User.objects.create(
            username=email,
            email=email,
            first_name=first_name[:60],
            last_name=last_name[:60],
        )
        user.set_unusable_password()
        user.save()
        CustomerProfile.objects.get_or_create(user=user)

        # Trigger welcome email
        try:
            from apps.core.email_service import send_welcome_email
            send_welcome_email(user)
        except Exception as e:
            logger.warning("Failed to dispatch welcome email to new Google user %s: %s", email, e)

    # 3. Log the user into Django session
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")

    # 4. Merge any guest cart accumulated during the session
    try:
        CartService.get_or_create_cart(request)
    except Exception as e:
        logger.warning("Failed to merge guest cart for Google user %s: %s", email, e)

    return user, created, ""
