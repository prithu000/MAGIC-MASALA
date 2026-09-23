"""
apps/coupons/models.py
Coupon, CouponUsage
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class Coupon(models.Model):
    class DiscountType(models.TextChoices):
        FLAT = "flat", "Flat (₹ off)"
        PERCENTAGE = "percent", "Percentage (% off)"

    class AppliesTo(models.TextChoices):
        ALL = "all", "All Orders"
        PRODUCTS = "products", "Specific Products"
        CATEGORIES = "categories", "Specific Categories"
        COMBOS = "combos", "Combos Only"

    code = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=255, blank=True)
    discount_type = models.CharField(max_length=10, choices=DiscountType.choices, default=DiscountType.FLAT)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    max_discount_cap = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum discount amount for percentage coupons. Leave blank for no cap.",
    )
    min_cart_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Minimum order value for this coupon to be valid.",
    )
    valid_from = models.DateTimeField(default=timezone.now, help_text="Start date & time.")
    valid_to = models.DateTimeField(null=True, blank=True, help_text="Expiry date & time. Leave blank for no expiry.")
    is_active = models.BooleanField(default=True)
    usage_limit_total = models.PositiveIntegerField(
        null=True, blank=True, help_text="Maximum total uses. Leave blank for unlimited."
    )
    usage_limit_per_customer = models.PositiveIntegerField(
        null=True, blank=True, help_text="Maximum uses per customer. Leave blank for unlimited."
    )
    first_order_only = models.BooleanField(default=False, help_text="Only valid on a customer's first order.")
    applies_to = models.CharField(max_length=15, choices=AppliesTo.choices, default=AppliesTo.ALL)
    applicable_products = models.ManyToManyField("catalog.Product", blank=True)
    applicable_categories = models.ManyToManyField("catalog.Category", blank=True)
    show_on_announcement_bar = models.BooleanField(
        default=False, help_text="Show this coupon code in the announcement bar."
    )

    class Meta:
        ordering = ["-valid_from"]

    def __str__(self):
        return self.code

    @property
    def is_currently_valid(self) -> bool:
        now = timezone.now()
        if not self.is_active:
            return False
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_to and now > self.valid_to:
            return False
        return True


class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="usages")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE)
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("coupon", "order")]

    def __str__(self):
        return f"{self.coupon.code} — {self.user.email} — {self.used_at.date()}"
