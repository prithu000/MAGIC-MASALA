"""apps/combos/views.py"""

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.models import SiteSettings

from .models import CustomComboSelection, CustomizeComboRule, FixedCombo


def combo_list(request):
    from apps.cms.models import HeroSlide
    hero_slides = HeroSlide.objects.filter(is_active=True, placement=HeroSlide.Placement.COMBOS).order_by("display_order")
    combos = FixedCombo.objects.filter(is_active=True)
    return render(request, "combos/combo_list.html", {"combos": combos, "hero_slides": hero_slides})


def fixed_combo_detail(request, slug):
    combo = get_object_or_404(FixedCombo, slug=slug, is_active=True)
    return render(request, "combos/combo_detail.html", {"combo": combo})


def combo_builder(request):
    """Build-Your-Own combo page."""
    from apps.cms.models import HeroSlide
    hero_slides = HeroSlide.objects.filter(is_active=True, placement=HeroSlide.Placement.BUILD_COMBO).order_by("display_order")
    rule = CustomizeComboRule.objects.filter(is_active=True).first()
    if not rule:
        from django.http import Http404
        raise Http404("No active combo rule found.")

    settings = SiteSettings.get_solo()
    eligible_products = rule.get_eligible_products().select_related("category").prefetch_related("gallery_images")
    combo_price = rule.fixed_price if (rule.fixed_price and rule.fixed_price > 0) else settings.customize_combo_price

    # Get unique categories from eligible products for filter tabs
    from apps.catalog.models import Category
    category_ids = eligible_products.values_list("category_id", flat=True).distinct()
    categories = Category.objects.filter(pk__in=category_ids, is_active=True).order_by("display_order", "name")

    return render(
        request,
        "combos/combo_builder.html",
        {
            "rule": rule,
            "hero_slides": hero_slides,
            "eligible_products": eligible_products,
            "settings": settings,
            "required_count": rule.required_item_count,
            "max_units_per_product": rule.max_units_per_product,
            "combo_price": combo_price,
            "categories": categories,
        },
    )


from apps.core.security import ratelimit


@require_POST
@ratelimit(rate="30/m", key="ip")
def save_custom_combo(request):
    """Called by Alpine.js when the customer completes their selection."""
    import json
    from collections import Counter

    rule = CustomizeComboRule.objects.filter(is_active=True).first()
    if not rule:
        return JsonResponse({"error": "No active combo rule found."}, status=400)

    settings = SiteSettings.get_solo()
    combo_price = rule.fixed_price if (rule.fixed_price and rule.fixed_price > 0) else settings.customize_combo_price

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid request format."}, status=400)
    items_data = data.get("items")
    if not items_data:
        raw_ids = data.get("product_ids", [])
        items_data = dict(Counter(raw_ids))

    cleaned_items = {}
    total_qty = 0
    for pid_str, qty in items_data.items():
        try:
            pid = int(pid_str)
            qty = int(qty)
            if qty > 0:
                cleaned_items[pid] = qty
                total_qty += qty
        except (ValueError, TypeError):
            continue

    if total_qty != rule.required_item_count:
        return JsonResponse(
            {"error": f"Please select exactly {rule.required_item_count} items (currently {total_qty})."},
            status=400,
        )

    max_per_product = rule.max_units_per_product or 2
    for pid, qty in cleaned_items.items():
        if qty > max_per_product:
            return JsonResponse(
                {"error": f"You can select at most {max_per_product} units of any individual spice."},
                status=400,
            )

    from apps.catalog.models import Product
    products = Product.objects.filter(
        pk__in=cleaned_items.keys(),
        is_active=True,
        is_customize_combo_eligible=True,
    )

    if products.count() != len(cleaned_items):
        return JsonResponse({"error": "One or more selected products are not eligible."}, status=400)

    selection = CustomComboSelection.objects.create(
        rule=rule,
        user=request.user if request.user.is_authenticated else None,
        session_key=request.session.session_key or "",
        is_complete=True,
        combo_price=combo_price,
        free_product=rule.free_product,
        items_json={str(k): v for k, v in cleaned_items.items()},
    )
    selection.selected_products.set(products)

    # Add to cart
    from apps.cart.services import CartService
    CartService.add_item(request, custom_combo_id=selection.pk)

    return JsonResponse({"redirect": "/cart/"})
