"""
apps/cart/models.py
Cart and CartItem — supports guest (session-based) and authenticated users.
"""

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name="cart")
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    coupon = models.ForeignKey(
        "coupons.Coupon",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="carts",
    )

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        if self.user:
            return f"Cart — {self.user.email}"
        return f"Guest Cart — {self.session_key}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cart_items",
    )
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cart_items",
    )
    fixed_combo = models.ForeignKey(
        "combos.FixedCombo",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cart_items",
    )
    custom_combo_selection = models.ForeignKey(
        "combos.CustomComboSelection",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cart_items",
    )
    quantity = models.PositiveSmallIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["added_at"]

    def __str__(self):
        if self.product:
            label = str(self.variant or self.product)
        elif self.fixed_combo:
            label = str(self.fixed_combo)
        else:
            label = "Custom combo"
        return f"{self.quantity}× {label}"

    @property
    def unit_price(self):
        """Return the unit price for this cart item."""
        if self.product:
            if self.variant:
                return self.variant.price
            return self.product.price
        if self.fixed_combo:
            return self.fixed_combo.combo_price
        if self.custom_combo_selection:
            from apps.core.models import SiteSettings
            return SiteSettings.get_solo().customize_combo_price
        return 0

    @property
    def line_total(self):
        return self.unit_price * self.quantity
