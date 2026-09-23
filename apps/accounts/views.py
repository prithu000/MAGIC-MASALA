"""
apps/accounts/views.py
"""

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.orders.models import Order
from .forms import AddressForm, CustomerRegistrationForm, ProfileForm
from .models import Address, Wishlist

from django.views.decorators.http import require_POST
from apps.core.security import ratelimit

User = get_user_model()


@ratelimit(rate="5/m", key="ip")
def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    if request.method == "POST":
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, "Welcome to MU Magic Masala! Your account has been created.")
            return redirect("accounts:dashboard")
    else:
        form = CustomerRegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def dashboard(request):
    recent_orders = Order.objects.filter(user=request.user).order_by("-created_at")[:5]
    return render(request, "accounts/dashboard.html", {"recent_orders": recent_orders})


@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "accounts/orders.html", {"orders": orders})


@login_required
def order_detail(request, order_number):
    from django.http import Http404
    order = get_object_or_404(Order, order_number=order_number)

    # Permission check:
    # 1. Staff / Superuser can always view customer orders
    # 2. Owner of the order (exact user match)
    # 3. Placed in current guest session
    is_authorized = (
        request.user.is_staff
        or request.user.is_superuser
        or order.user_id == request.user.id
        or request.session.get("confirmed_order") == order.pk
    )
    if not is_authorized:
        raise Http404("No Order matches the given query.")

    return render(request, "accounts/order_detail.html", {"order": order})


@login_required
def address_list(request):
    addresses = request.user.addresses.all()
    return render(request, "accounts/address_list.html", {"addresses": addresses})


@login_required
def address_create(request):
    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(request, "Address saved.")
            return redirect("accounts:address_list")
    else:
        form = AddressForm()
    return render(request, "accounts/address_form.html", {"form": form, "title": "Add Address"})


@login_required
def address_edit(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == "POST":
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, "Address updated.")
            return redirect("accounts:address_list")
    else:
        form = AddressForm(instance=address)
    return render(request, "accounts/address_form.html", {"form": form, "title": "Edit Address"})


@login_required
@require_POST
def address_delete(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    address.delete()
    messages.success(request, "Address removed.")
    return redirect("accounts:address_list")


@login_required
@require_POST
def address_set_default(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    address.is_default = True
    address.save()
    messages.success(request, "Default address updated.")
    return redirect("accounts:address_list")


@login_required
def wishlist(request):
    items = Wishlist.objects.filter(user=request.user).select_related("product")
    return render(request, "accounts/wishlist.html", {"items": items})


@login_required
@require_POST
@ratelimit(rate="30/m", key="user_or_ip")
def wishlist_toggle(request, product_id):
    from apps.catalog.models import Product

    product = get_object_or_404(Product, pk=product_id, is_active=True)
    obj, created = Wishlist.objects.get_or_create(user=request.user, product=product)
    if not created:
        obj.delete()
        in_wishlist = False
    else:
        in_wishlist = True

    if request.headers.get("HX-Request"):
        return JsonResponse({"in_wishlist": in_wishlist})

    return redirect(request.META.get("HTTP_REFERER", "accounts:wishlist"))


@login_required
def profile_edit(request):
    profile = request.user.profile
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("accounts:profile_edit")
    else:
        form = ProfileForm(instance=profile, user=request.user)
    return render(request, "accounts/profile_edit.html", {"form": form})


from django.contrib.auth import views as auth_views
from apps.core.email_service import send_password_changed_email


class CustomPasswordChangeView(auth_views.PasswordChangeView):
    template_name = "accounts/password_change.html"
    success_url = "/account/password-change/done/"

    def form_valid(self, form):
        response = super().form_valid(form)
        try:
            send_password_changed_email(self.request.user)
        except Exception:
            pass
        return response


class CustomPasswordResetView(auth_views.PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "emails/password_reset.html"
    html_email_template_name = "emails/password_reset.html"
    subject_template_name = "emails/password_reset_subject.txt"
    success_url = "/account/password-reset/done/"


# ---------------------------------------------------------------------------
# Google OAuth 2.0 & Sign-In Views
# ---------------------------------------------------------------------------
import hmac
import logging
import secrets
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt

from .google_auth import (
    is_google_auth_configured,
    get_google_redirect_uri,
    build_google_authorization_url,
    exchange_code_for_tokens,
    fetch_google_userinfo,
    verify_google_id_token,
    authenticate_or_register_google_user,
)

_oauth_logger = logging.getLogger("apps.accounts.oauth")

@ratelimit(rate="10/m", key="ip")
def google_login(request):
    """
    Initiates Google OAuth 2.0 flow.
    Generates a cryptographically random anti-CSRF state token and redirects to Google.
    """
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    if not is_google_auth_configured():
        messages.warning(
            request,
            "Google Sign-In is not configured yet. Please configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your environment.",
        )
        return redirect("accounts:login")

    # Determine safe return target
    raw_next = request.GET.get("next") or request.POST.get("next") or "/account/"
    allowed_hosts = {request.get_host()}
    if not url_has_allowed_host_and_scheme(raw_next, allowed_hosts=allowed_hosts, require_https=request.is_secure()):
        raw_next = "/account/"

    # Generate state token and store in session
    state = secrets.token_urlsafe(32)
    request.session["google_oauth_state"] = state
    request.session["google_oauth_next"] = raw_next

    redirect_uri = get_google_redirect_uri(request)
    _oauth_logger.debug("[Google OAuth] Initiating flow. redirect_uri=%s", redirect_uri)
    request.session["google_oauth_redirect_uri"] = redirect_uri
    auth_url = build_google_authorization_url(request, redirect_uri, state)
    return redirect(auth_url)


def google_callback(request):
    """
    Handles Google OAuth 2.0 redirect callback.
    Verifies state token, exchanges code for user profile, logs in or registers user.
    """
    error = request.GET.get("error")
    if error:
        _oauth_logger.warning("[Google OAuth] Callback error from Google: %s", error)
        messages.error(request, "Google sign-in was cancelled or encountered an error. Please try again.")
        return redirect("accounts:login")

    # Anti-CSRF state verification — uses constant-time compare to prevent timing attacks
    saved_state = request.session.pop("google_oauth_state", None)
    received_state = request.GET.get("state")
    if not saved_state or not received_state or not hmac.compare_digest(saved_state, received_state):
        _oauth_logger.warning("[Google OAuth] State mismatch — possible CSRF attempt from IP: %s", request.META.get("REMOTE_ADDR"))
        messages.error(request, "Security check failed (invalid session state). Please try signing in again.")
        return redirect("accounts:login")

    code = request.GET.get("code", "")
    if not code or len(code) > 512:  # Sanity check — real auth codes are ~60-200 chars
        messages.error(request, "Authorization code missing or invalid.")
        return redirect("accounts:login")

    redirect_uri = request.session.pop("google_oauth_redirect_uri", None) or get_google_redirect_uri(request)
    tokens = exchange_code_for_tokens(code, redirect_uri)
    if not tokens or not tokens.get("access_token"):
        messages.error(request, "Failed to authenticate with Google servers. Please try again.")
        return redirect("accounts:login")

    user_info = fetch_google_userinfo(tokens["access_token"])
    if not user_info:
        messages.error(request, "Failed to retrieve your Google profile. Please try again.")
        return redirect("accounts:login")

    user, created, err = authenticate_or_register_google_user(request, user_info)
    if err or not user:
        messages.error(request, err or "Could not sign in with Google.")
        return redirect("accounts:login")

    next_url = request.session.pop("google_oauth_next", "/account/")
    allowed_hosts = {request.get_host()}
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts=allowed_hosts, require_https=request.is_secure()):
        next_url = "/account/"

    display_name = user.first_name or user.email
    if created:
        messages.success(request, f"Welcome to MU Magic Masala, {display_name}! Your account has been created via Google.")
    else:
        messages.success(request, f"Welcome back, {display_name}! Successfully signed in with Google.")

    _oauth_logger.info("[Google OAuth] User %s logged in (created=%s)", user.email, created)
    return redirect(next_url)


@csrf_exempt
@require_POST
def google_credential(request):
    """
    Handles Google One-Tap or Google Identity Services credential (JWT ID token) POST.
    """
    body_data = {}
    id_token = request.POST.get("credential")
    if not id_token:
        try:
            import json
            body_data = json.loads(request.body)
            id_token = body_data.get("credential")
        except Exception:
            pass

    if not id_token:
        return JsonResponse({"success": False, "error": "Missing Google credential"}, status=400)

    token_data = verify_google_id_token(id_token)
    if not token_data:
        return JsonResponse({"success": False, "error": "Invalid or expired Google credential"}, status=400)

    user, created, err = authenticate_or_register_google_user(request, token_data)
    if err or not user:
        return JsonResponse({"success": False, "error": err or "Authentication failed"}, status=400)

    display_name = user.first_name or user.email
    if created:
        messages.success(request, f"Welcome to MU Magic Masala, {display_name}! Your account has been created via Google.")
    else:
        messages.success(request, f"Welcome back, {display_name}! Successfully signed in with Google.")

    next_url = request.POST.get("next") or body_data.get("next") or request.GET.get("next") or "/account/"
    allowed_hosts = {request.get_host()}
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts=allowed_hosts, require_https=request.is_secure()):
        next_url = "/account/"

    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.content_type == "application/json":
        return JsonResponse({"success": True, "redirect": next_url})

    return redirect(next_url)


