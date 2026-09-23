"""apps/cart/views.py — Fast reactive cart views with JSON & form support."""

import json
from decimal import Decimal

from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.core.security import ratelimit
from apps.coupons.services import CouponService, CouponError
from .services import CartService


def cart_detail(request):
    totals = CartService.compute_totals(request)
    totals["coupon_alert"] = request.session.pop("coupon_alert", None)
    return render(request, "cart/cart.html", totals)


@require_POST
@ratelimit(rate="60/m", key="user_or_ip")
def cart_add(request):
    from apps.catalog.models import Product, ProductVariant
    from apps.combos.models import FixedCombo

    if request.content_type == "application/json":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
    else:
        data = request.POST

    try:
        quantity = int(data.get("quantity", 1))
    except (ValueError, TypeError):
        quantity = 1

    try:
        CartService.add_item(
            request,
            product_id=data.get("product_id"),
            variant_id=data.get("variant_id"),
            combo_id=data.get("combo_id"),
            quantity=quantity,
        )
    except (Product.DoesNotExist, ProductVariant.DoesNotExist, FixedCombo.DoesNotExist, ValueError) as e:
        err_msg = str(e) or "Selected product or variant is unavailable."
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.GET.get("format") == "json" or request.content_type == "application/json":
            return JsonResponse({"error": err_msg, "success": False}, status=400)
        messages.error(request, err_msg)
        return redirect("cart:detail")

    if str(data.get("buy_now")).lower() in ("true", "1", "yes"):
        return redirect("orders:checkout")
    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.GET.get("format") == "json":
        totals = CartService.compute_totals(request)
        return JsonResponse({
            "success": True,
            "total_items": len(totals["items"]),
            "subtotal": str(totals["subtotal"]),
            "tax_amount": str(totals["tax_amount"]),
            "total": str(totals["total"]),
        })
    return redirect("cart:detail")


@require_POST
def cart_update(request, item_id):
    if request.content_type == "application/json":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        raw_qty = data.get("quantity", 1)
    else:
        raw_qty = request.POST.get("quantity", 1)

    try:
        quantity = int(raw_qty)
    except (ValueError, TypeError):
        quantity = 1

    updated_item = CartService.update_item(request, item_id, quantity)
    totals = CartService.compute_totals(request)

    # If AJAX / Fetch
    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.GET.get("format") == "json" or request.content_type == "application/json":
        return JsonResponse({
            "success": True,
            "item_id": item_id,
            "quantity": updated_item.quantity if updated_item else 0,
            "line_total": str(updated_item.line_total) if updated_item else "0.00",
            "item_deleted": updated_item is None,
            "subtotal": str(totals["subtotal"]),
            "discount": str(totals["discount"]),
            "tax_amount": str(totals["tax_amount"]),
            "shipping": str(totals["shipping"]),
            "free_shipping": totals["free_shipping"],
            "total": str(totals["total"]),
            "meets_minimum": totals["meets_minimum"],
            "shortfall": str(totals["shortfall"]),
            "shipping_shortfall": str(totals["shipping_shortfall"]),
            "total_items_count": len(totals["items"]),
        })

    return redirect("cart:detail")


@require_POST
def cart_remove(request, item_id):
    CartService.remove_item(request, item_id)
    totals = CartService.compute_totals(request)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.GET.get("format") == "json" or request.content_type == "application/json":
        return JsonResponse({
            "success": True,
            "item_id": item_id,
            "subtotal": str(totals["subtotal"]),
            "discount": str(totals["discount"]),
            "tax_amount": str(totals["tax_amount"]),
            "shipping": str(totals["shipping"]),
            "free_shipping": totals["free_shipping"],
            "total": str(totals["total"]),
            "meets_minimum": totals["meets_minimum"],
            "shortfall": str(totals["shortfall"]),
            "total_items_count": len(totals["items"]),
        })

    return redirect("cart:detail")


@require_POST
@ratelimit(rate="15/m", key="user_or_ip")
def apply_coupon(request):
    if request.content_type == "application/json":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        code = data.get("coupon_code", "")
    else:
        code = request.POST.get("coupon_code", "")

    cart = CartService.get_or_create_cart(request)
    success = False
    message = ""
    coupon_obj = None

    try:
        coupon_obj = CouponService.validate(code, request.user, cart)
        cart.coupon = coupon_obj
        cart.save()
        message = f'Coupon "{coupon_obj.code}" applied successfully!'
        success = True
    except CouponError as e:
        message = str(e)
        success = False

    totals = CartService.compute_totals(request)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.GET.get("format") == "json" or request.content_type == "application/json":
        return JsonResponse({
            "success": success,
            "message": message,
            "coupon_code": coupon_obj.code if success else "",
            "discount": str(totals["discount"]),
            "subtotal": str(totals["subtotal"]),
            "tax_amount": str(totals["tax_amount"]),
            "shipping": str(totals["shipping"]),
            "free_shipping": totals["free_shipping"],
            "total": str(totals["total"]),
        })

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    request.session["coupon_alert"] = {"success": success, "message": message}
    return redirect("cart:detail")


@require_POST
def remove_coupon(request):
    cart = CartService.get_or_create_cart(request)
    cart.coupon = None
    cart.save()
    request.session.pop("coupon_alert", None)

    totals = CartService.compute_totals(request)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.GET.get("format") == "json" or request.content_type == "application/json":
        return JsonResponse({
            "success": True,
            "message": "Coupon removed.",
            "subtotal": str(totals["subtotal"]),
            "discount": "0.00",
            "tax_amount": str(totals["tax_amount"]),
            "shipping": str(totals["shipping"]),
            "free_shipping": totals["free_shipping"],
            "total": str(totals["total"]),
        })

    messages.info(request, "Coupon removed.")
    return redirect("cart:detail")
