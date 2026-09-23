"""
apps/core/admin_views.py — Custom views for the Django Unfold Admin Panel.
Provides the interactive Store Owner Manual & Operations Guide.
"""

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from apps.catalog.models import Product
from apps.combos.models import CustomizeComboRule, FixedCombo
from apps.cms.models import HeroSlide, InfluencerReel
from apps.orders.models import Order
from apps.coupons.models import Coupon
from apps.reviews.models import ProductReview
from apps.cart.models import Cart


@staff_member_required
def admin_guide_view(request):
    """
    Comprehensive, interactive Store Owner Manual for MU Magic Masala.
    Explains each admin feature in plain, simple Hindi & English.
    """
    context = admin.site.each_context(request)
    
    # Store quick stats for owner reference
    featured_combo = FixedCombo.objects.filter(is_featured_on_homepage=True).first()
    active_rule = CustomizeComboRule.objects.filter(is_active=True).first()
    
    stats = {
        "total_products": Product.objects.count(),
        "out_of_stock": Product.objects.filter(stock_quantity=0).count(),
        "pending_orders": Order.objects.filter(order_status__in=["placed", "confirmed", "packed"]).count(),
        "featured_combo": featured_combo.name if featured_combo else "None set",
        "byo_rule": f"{active_rule.required_item_count} items for ₹{active_rule.fixed_price}" if active_rule else "Inactive",
        "active_slides": HeroSlide.objects.filter(is_active=True).count(),
        "pending_reviews": ProductReview.objects.filter(is_approved=False).count(),
        "active_coupons": Coupon.objects.filter(is_active=True).count(),
        "active_carts": Cart.objects.filter(items__isnull=False).distinct().count(),
    }
    
    context.update({
        "title": "Store Owner Manual & Operations Guide",
        "subtitle": "Admin Panel use karne ka sampurna guide (संपूर्ण गाइड)",
        "stats": stats,
    })
    
    return render(request, "admin/guide.html", context)
