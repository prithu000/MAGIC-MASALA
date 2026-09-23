"""
apps/orders/views.py — Checkout flow: Address → Payment → Confirmation
"""

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.cart.services import CartService
from apps.core.models import SiteSettings
from apps.core.security import ratelimit
from apps.coupons.services import CouponService
from .models import Order, OrderItem, OrderStatusHistory
from .tasks import send_order_confirmation_email


def validate_shipping_address(data):
    """
    Strict anti-spam validation for shipping addresses.
    Rejects fake names (DFGH), fake phone numbers (DFG / 0000000000), gibberish addresses, and invalid PIN codes.
    Returns (cleaned_data, errors_dict).
    """
    import re
    errors = {}
    cleaned = {}

    # 1. Full Name
    full_name = (data.get("full_name") or "").strip()
    if len(full_name) < 3:
        errors["full_name"] = "Full name must be at least 3 characters."
    elif not re.match(r"^[A-Za-z\s.'-]+$", full_name):
        errors["full_name"] = "Full name can only contain letters and spaces."
    else:
        # Spam check: keyboard smash (e.g., 'DFGH', 'asdf', words >= 3 chars with no vowels)
        words = full_name.split()
        for w in words:
            if len(w) >= 3 and not re.search(r"[aeiouAEIOU]", w):
                errors["full_name"] = "Please enter a genuine, recognizable full name (e.g. Rahul Sharma)."
                break
            if re.search(r"(.)\1\1", w):
                errors["full_name"] = "Please enter a valid real name without repeated characters."
                break
    cleaned["full_name"] = full_name

    # 2. Phone Number
    raw_phone = re.sub(r"\D", "", data.get("phone") or "")
    if len(raw_phone) == 12 and raw_phone.startswith("91"):
        raw_phone = raw_phone[2:]
    elif len(raw_phone) == 11 and raw_phone.startswith("0"):
        raw_phone = raw_phone[1:]

    if not re.match(r"^[6-9]\d{9}$", raw_phone):
        errors["phone"] = "Please enter a valid 10-digit Indian mobile number (e.g. 9876543210)."
    elif re.match(r"^(.)\1{9}$", raw_phone) or raw_phone in ("1234567890", "0123456789"):
        errors["phone"] = "Please enter an active, genuine mobile number."
    cleaned["phone"] = raw_phone

    # 3. Address Line 1
    addr1 = (data.get("address_line1") or "").strip()
    if len(addr1) < 6:
        errors["address_line1"] = "Please enter complete flat/house no., building and street address."
    else:
        words = [w for w in re.split(r"\s+|,|-", addr1) if len(w) >= 3]
        if words and all(not re.search(r"[aeiouAEIOU0-9]", w) for w in words):
            errors["address_line1"] = "Please enter a genuine delivery address (not random letters)."
    cleaned["address_line1"] = addr1
    cleaned["address_line2"] = (data.get("address_line2") or "").strip()
    cleaned["landmark"] = (data.get("landmark") or "").strip()

    # 4. PIN Code
    pincode = re.sub(r"\D", "", data.get("pincode") or "")
    if not re.match(r"^\d{6}$", pincode):
        errors["pincode"] = "Please enter a valid 6-digit Indian PIN code."
    cleaned["pincode"] = pincode

    # 5. City and District
    city = (data.get("city") or "").strip()
    district = (data.get("district") or "").strip()
    state = (data.get("state") or "").strip()

    if not city and not district:
        errors["city"] = "City / Town is required."
    elif not city:
        city = district
    elif not district:
        district = city

    if not state:
        errors["state"] = "State is required."

    cleaned["city"] = city
    cleaned["district"] = district
    cleaned["state"] = state

    return cleaned, errors


def checkout_address(request):
    """Step 1: Select or enter a shipping address with strict anti-spam validation."""
    cart_data = CartService.compute_totals(request)

    if not cart_data["meets_minimum"]:
        messages.warning(
            request,
            f"Add ₹{cart_data['shortfall']:.0f} more to reach the minimum order of "
            f"₹{cart_data['min_order_value']:.0f}.",
        )
        return redirect("cart:detail")

    if not cart_data["items"]:
        return redirect("cart:detail")

    addresses = []
    if request.user.is_authenticated:
        addresses = request.user.addresses.all()

    if request.method == "POST":
        address_id = request.POST.get("address_id")
        if address_id and request.user.is_authenticated:
            from apps.accounts.models import Address
            address = get_object_or_404(Address, pk=address_id, user=request.user)
            request.session["checkout_address_id"] = address.pk
            return redirect("orders:checkout_payment")
        else:
            # Guest or new address — perform strict anti-spam validation
            cleaned_data, errors = validate_shipping_address(request.POST)
            if errors:
                for field_name, err in errors.items():
                    messages.error(request, err)
                return render(
                    request,
                    "orders/checkout_address.html",
                    {
                        **cart_data,
                        "addresses": addresses,
                        "form_data": request.POST,
                        "errors": errors,
                    },
                )

            # Store verified address data in session
            display_city = cleaned_data["city"]
            if cleaned_data["district"] and cleaned_data["district"].lower() not in display_city.lower():
                display_city = f"{cleaned_data['city']}, Dist. {cleaned_data['district']}"

            request.session["checkout_address_data"] = {
                "full_name": cleaned_data["full_name"],
                "phone": cleaned_data["phone"],
                "address_line1": cleaned_data["address_line1"],
                "address_line2": cleaned_data["address_line2"],
                "landmark": cleaned_data["landmark"],
                "city": display_city,
                "district": cleaned_data["district"],
                "state": cleaned_data["state"],
                "pincode": cleaned_data["pincode"],
            }

            # If user is logged in, automatically save address to their account
            if request.user.is_authenticated:
                from apps.accounts.models import Address
                address, _ = Address.objects.get_or_create(
                    user=request.user,
                    address_line1=cleaned_data["address_line1"],
                    pincode=cleaned_data["pincode"],
                    defaults={
                        "full_name": cleaned_data["full_name"],
                        "phone": cleaned_data["phone"],
                        "address_line2": cleaned_data["address_line2"],
                        "landmark": cleaned_data["landmark"],
                        "city": display_city,
                        "state": cleaned_data["state"],
                        "is_default": not request.user.addresses.exists(),
                    },
                )
                request.session["checkout_address_id"] = address.pk

            return redirect("orders:checkout_payment")

    return render(
        request,
        "orders/checkout_address.html",
        {**cart_data, "addresses": addresses},
    )


def checkout_payment(request):
    """Step 2: Choose payment method and review order summary."""
    cart_data = CartService.compute_totals(request)
    settings = SiteSettings.get_solo()

    if not cart_data["items"]:
        return redirect("cart:detail")

    if request.method == "POST":
        return create_order(request)

    # Recalculate with COD for display
    cod_data = CartService.compute_totals(request, payment_method="cod")

    return render(
        request,
        "orders/checkout_payment.html",
        {
            **cart_data,
            "cod_data": cod_data,
            "settings": settings,
        },
    )


@require_POST
@ratelimit(rate="10/m", key="ip")
@transaction.atomic
def create_order(request):
    """Create the Order record and redirect to payment gateway or COD confirmation."""
    settings = SiteSettings.get_solo()
    payment_method = request.POST.get("payment_method") or request.session.get("checkout_payment_method", "online")
    if payment_method not in ("online", "cod"):
        payment_method = "online"
    request.session["checkout_payment_method"] = payment_method
    cart_data = CartService.compute_totals(request, payment_method=payment_method)

    if not cart_data["meets_minimum"]:
        return redirect("orders:checkout_address")

    # Build order
    order = Order(
        user=request.user if request.user.is_authenticated else None,
        payment_method=payment_method,
        subtotal=cart_data["subtotal"],
        discount_amount=cart_data["discount"],
        tax_amount=cart_data["tax_amount"],
        cod_charge_applied=cart_data["cod_charge"],
        shipping_charge=cart_data["shipping"],
        total=cart_data["total"],
        advance_amount=cart_data["cod_advance"],
        remaining_amount=cart_data["cod_remaining"],
    )

    # Snapshot address
    if request.user.is_authenticated and request.session.get("checkout_address_id"):
        from apps.accounts.models import Address
        address = Address.objects.filter(pk=request.session["checkout_address_id"], user=request.user).first()
        if not address:
            return redirect("orders:checkout_address")
        order.snapshot_address(address)
    elif request.session.get("checkout_address_data"):
        data = request.session["checkout_address_data"]
        for field, value in data.items():
            setattr(order, f"shipping_{field}", value)
        if request.user.is_authenticated:
            from apps.accounts.models import Address
            Address.objects.get_or_create(
                user=request.user,
                address_line1=data.get("address_line1", ""),
                pincode=data.get("pincode", ""),
                defaults={
                    "full_name": data.get("full_name", ""),
                    "phone": data.get("phone", ""),
                    "address_line2": data.get("address_line2", ""),
                    "landmark": data.get("landmark", ""),
                    "city": data.get("city", ""),
                    "state": data.get("state", ""),
                    "is_default": not request.user.addresses.exists(),
                },
            )
    else:
        return redirect("orders:checkout_address")

    # Coupon snapshot
    coupon = cart_data.get("coupon")
    if coupon:
        order.coupon = coupon
        order.coupon_code = coupon.code

    order.save()
    OrderStatusHistory.objects.create(order=order, status=Order.OrderStatus.PLACED, note="Order placed by customer.")

    # Save order items with snapshotted prices
    for item in cart_data["items"]:
        if item.custom_combo_selection:
            combo_items = item.custom_combo_selection.get_items()
            items_desc = ", ".join([f"{ci['quantity']}× {ci['product'].name}" for ci in combo_items])
            free_desc = f" + FREE {item.custom_combo_selection.free_product.name}" if item.custom_combo_selection.free_product else ""
            item_name = f"{item.custom_combo_selection.rule.name} ({items_desc}{free_desc})"
        elif item.product:
            item_name = str(item.variant or item.product)
        elif item.fixed_combo:
            item_name = str(item.fixed_combo)
        else:
            item_name = "Custom combo"

        OrderItem.objects.create(
            order=order,
            product=item.product,
            variant=item.variant,
            fixed_combo=item.fixed_combo,
            item_name=item_name,
            quantity=item.quantity,
            price_at_purchase=item.unit_price,
        )

    # Record coupon usage
    if coupon and request.user.is_authenticated:
        from apps.coupons.models import CouponUsage
        CouponUsage.objects.create(coupon=coupon, user=request.user, order=order)

    # Clear session checkout data
    for key in ("checkout_address_id", "checkout_address_data", "checkout_payment_method"):
        request.session.pop(key, None)

    # Clear cart
    cart = cart_data["cart"]
    cart.items.all().delete()
    cart.coupon = None
    cart.save()

    request.session["pending_order_id"] = order.pk

    if payment_method == "online":
        return redirect("payments:razorpay_checkout", order_id=order.pk)
    else:
        # COD (Direct confirmation for testing — no online advance required)
        request.session["confirmed_order"] = order.pk
        messages.success(request, f"Order #{order.order_number} has been placed successfully via Cash on Delivery!")
        try:
            from apps.core.email_service import send_order_confirmation_email
            send_order_confirmation_email(order)
        except Exception as e:
            logger.error("Failed to send COD order confirmation email: %s", e)
        return redirect("orders:order_confirmation", order_number=order.order_number)


def order_confirmation(request, order_number):
    """Confirmation page — display-only; no payment logic runs here."""
    order = get_object_or_404(Order, order_number=order_number)
    # Security: only show to the order owner or if it's in the session
    if request.user.is_authenticated and order.user != request.user:
        return redirect("cms:home")
    if not request.user.is_authenticated and request.session.get("confirmed_order") != order.pk:
        return redirect("cms:home")

    return render(request, "orders/confirmation.html", {"order": order})


# Indian State & City prefix mapping fallback
PIN_STATE_PREFIXES = {
    "11": ("Delhi", "Delhi"),
    "12": ("Haryana", "Gurgaon / Faridabad"),
    "13": ("Haryana", "Karnal / Panipat"),
    "14": ("Punjab", "Amritsar / Jalandhar"),
    "15": ("Punjab", "Bathinda / Firozpur"),
    "16": ("Chandigarh", "Chandigarh"),
    "17": ("Himachal Pradesh", "Shimla"),
    "18": ("Jammu & Kashmir", "Jammu"),
    "19": ("Jammu & Kashmir", "Srinagar"),
    "20": ("Uttar Pradesh", "Noida / Ghaziabad"),
    "21": ("Uttar Pradesh", "Allahabad"),
    "22": ("Uttar Pradesh", "Lucknow"),
    "23": ("Uttar Pradesh", "Varanasi"),
    "241": ("Uttar Pradesh", "Hardoi"),
    "242": ("Uttar Pradesh", "Shahjahanpur"),
    "243": ("Uttar Pradesh", "Budaun"),
    "244": ("Uttar Pradesh", "Moradabad"),
    "245": ("Uttar Pradesh", "Hapur"),
    "246": ("Uttarakhand", "Pauri Garhwal"),
    "247": ("Uttar Pradesh", "Saharanpur"),
    "248": ("Uttarakhand", "Dehradun"),
    "249": ("Uttarakhand", "Haridwar"),
    "24": ("Uttar Pradesh", "Western UP"),
    "25": ("Uttar Pradesh", "Meerut"),
    "26": ("Uttarakhand", "Nainital"),
    "27": ("Uttar Pradesh", "Gorakhpur"),
    "28": ("Uttar Pradesh", "Agra"),
    "30": ("Rajasthan", "Jaipur"),

    "31": ("Rajasthan", "Udaipur"),
    "32": ("Rajasthan", "Kota"),
    "33": ("Rajasthan", "Bikaner"),
    "34": ("Rajasthan", "Jodhpur"),
    "36": ("Gujarat", "Rajkot"),
    "37": ("Gujarat", "Jamnagar"),
    "38": ("Gujarat", "Ahmedabad"),
    "39": ("Gujarat", "Surat"),
    "40": ("Maharashtra", "Mumbai"),
    "41": ("Maharashtra", "Pune"),
    "42": ("Maharashtra", "Nashik"),
    "43": ("Maharashtra", "Chhatrapati Sambhajinagar"),
    "44": ("Maharashtra", "Nagpur"),
    "45": ("Madhya Pradesh", "Indore"),
    "46": ("Madhya Pradesh", "Bhopal"),
    "47": ("Madhya Pradesh", "Gwalior"),
    "48": ("Madhya Pradesh", "Jabalpur"),
    "49": ("Chhattisgarh", "Raipur"),
    "50": ("Telangana", "Hyderabad"),
    "51": ("Andhra Pradesh", "Tirupati"),
    "52": ("Andhra Pradesh", "Vijayawada"),
    "53": ("Andhra Pradesh", "Visakhapatnam"),
    "56": ("Karnataka", "Bengaluru"),
    "57": ("Karnataka", "Mangalore"),
    "58": ("Karnataka", "Hubli"),
    "59": ("Karnataka", "Belgaum"),
    "60": ("Tamil Nadu", "Chennai"),
    "61": ("Tamil Nadu", "Thanjavur"),
    "62": ("Tamil Nadu", "Madurai"),
    "63": ("Tamil Nadu", "Salem"),
    "64": ("Tamil Nadu", "Coimbatore"),
    "67": ("Kerala", "Kozhikode"),
    "68": ("Kerala", "Kochi"),
    "69": ("Kerala", "Thiruvananthapuram"),
    "70": ("West Bengal", "Kolkata"),
    "71": ("West Bengal", "Howrah"),
    "72": ("West Bengal", "Midnapore"),
    "73": ("West Bengal", "Siliguri"),
    "74": ("West Bengal", "North 24 Parganas"),
    "75": ("Odisha", "Bhubaneswar"),
    "76": ("Odisha", "Cuttack"),
    "77": ("Odisha", "Sambalpur"),
    "78": ("Assam", "Guwahati"),
    "79": ("North East", "Shillong"),
    "80": ("Bihar", "Patna"),
    "81": ("Bihar", "Bhagalpur"),
    "82": ("Bihar", "Gaya"),
    "83": ("Jharkhand", "Ranchi"),
    "84": ("Bihar", "Muzaffarpur"),
    "85": ("Bihar", "Purnia"),
}


@ratelimit(rate="30/m", key="ip")
def pincode_lookup(request, pincode):
    """Look up Indian PIN code: auto-verifies and returns city/district and state."""
    import json
    import re
    import urllib.request
    from django.core.cache import cache
    from django.http import JsonResponse

    pincode = str(pincode).strip()
    if not re.match(r"^\d{6}$", pincode):
        return JsonResponse(
            {"valid": False, "error": "Please enter a valid 6-digit Indian PIN code."},
            status=400,
        )

    cache_key = f"pincode_info_{pincode}"
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached)

    city = ""
    district = ""
    state = ""
    valid = False

    # 1. Try Postal Pincode API
    try:
        url = f"https://api.postalpincode.in/pincode/{pincode}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and isinstance(data, list) and data[0].get("Status") == "Success":
                po_list = data[0].get("PostOffice") or []
                if po_list:
                    first_po = po_list[0]
                    district = first_po.get("District") or ""
                    state = first_po.get("State") or ""

                    # Extract City / Town / Tehsil / Block:
                    # Look for Block first (e.g. Sahaswan for Budaun)
                    blocks = [
                        p.get("Block")
                        for p in po_list
                        if p.get("Block") and p.get("Block") != "NA"
                    ]
                    if blocks:
                        city = blocks[0]
                    else:
                        names = [p.get("Name") for p in po_list if p.get("Name")]
                        city = names[0] if names else district

                    if not district and city:
                        district = city
                    valid = True
    except Exception:
        pass

    # 2. Fallback to postal prefix mapping if external API fails or times out
    if not valid:
        prefix3 = pincode[:3]
        prefix2 = pincode[:2]
        match = PIN_STATE_PREFIXES.get(prefix3) or PIN_STATE_PREFIXES.get(prefix2)
        if match:
            fallback_state, fallback_city = match
            state = fallback_state
            district = fallback_city
            city = fallback_city
            valid = True


    if valid:
        result = {
            "valid": True,
            "pincode": pincode,
            "city": city,
            "district": district,
            "state": state,
            "message": f"Verified: {city}, Dist. {district}, {state}",
        }
        cache.set(cache_key, result, 60 * 60 * 24 * 7)  # 7 days cache
        return JsonResponse(result)
    else:
        return JsonResponse(
            {"valid": False, "error": "Invalid Indian PIN code. Please check."},
            status=404,
        )

