"""apps/coupons/admin.py"""

from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Coupon, CouponUsage


@admin.register(Coupon)
class CouponAdmin(ModelAdmin):
    list_display = (
        "code",
        "discount_type",
        "discount_value",
        "valid_from",
        "valid_to",
        "is_active",
        "usage_count",
    )
    list_filter = ("is_active", "discount_type", "first_order_only")
    search_fields = ("code", "description")
    filter_horizontal = ("applicable_products", "applicable_categories")

    fieldsets = (
        (None, {"fields": ("code", "description", "is_active")}),
        (
            "Discount",
            {"fields": ("discount_type", "discount_value", "max_discount_cap", "min_cart_value")},
        ),
        ("Validity", {"fields": ("valid_from", "valid_to")}),
        (
            "Usage Limits",
            {"fields": ("usage_limit_total", "usage_limit_per_customer", "first_order_only")},
        ),
        (
            "Scope",
            {"fields": ("applies_to", "applicable_products", "applicable_categories")},
        ),
        ("Display", {"fields": ("show_on_announcement_bar",)}),
    )

    @admin.display(description="Times used")
    def usage_count(self, obj):
        return obj.usages.count()


@admin.register(CouponUsage)
class CouponUsageAdmin(ModelAdmin):
    list_display = ("coupon", "user", "order", "used_at")
    list_filter = ("coupon",)
    readonly_fields = [f.name for f in CouponUsage._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
