"""
apps/coupons/services.py
CouponService — validates a coupon code and computes the discount.
"""

from decimal import Decimal

from django.utils import timezone


class CouponError(Exception):
    """Raised when a coupon is invalid for any reason."""


class CouponService:

    @staticmethod
    def validate(code: str, user, cart) -> "Coupon":
        """
        Validate a coupon code.
        Returns the Coupon if valid.
        Raises CouponError with a human-readable message if not.
        """
        from .models import Coupon

        code = (code or "").strip()
        if not code:
            raise CouponError("Please enter a coupon code.")

        coupon = Coupon.objects.filter(code__iexact=code).first()
        if not coupon:
            raise CouponError(f'Coupon "{code}" does not exist or is invalid.')

        now = timezone.now()

        if not coupon.is_active:
            raise CouponError("This coupon is no longer active.")

        if coupon.valid_from and now < coupon.valid_from:
            raise CouponError("This coupon is not yet valid.")

        if coupon.valid_to and now > coupon.valid_to:
            raise CouponError("This coupon has expired.")

        # Cart minimum
        subtotal = sum(item.line_total for item in cart.items.all())
        if subtotal < coupon.min_cart_value:
            raise CouponError(
                f"This coupon requires a minimum order of ₹{coupon.min_cart_value:.0f}. "
                f"Your cart total is ₹{subtotal:.0f}."
            )

        # Total usage limit
        if coupon.usage_limit_total is not None:
            used = coupon.usages.count()
            if used >= coupon.usage_limit_total:
                raise CouponError("This coupon has reached its usage limit.")

        # Per-customer limit
        if coupon.usage_limit_per_customer is not None:
            if not (user and user.is_authenticated):
                raise CouponError("Please log in to your account to apply this coupon.")
            user_uses = coupon.usages.filter(user=user).count()
            if user_uses >= coupon.usage_limit_per_customer:
                raise CouponError("You have already used this coupon the maximum number of times.")

        # First order only
        if coupon.first_order_only:
            if not (user and user.is_authenticated):
                raise CouponError("Please log in to apply this first-order discount coupon.")
            from apps.orders.models import Order
            has_orders = Order.objects.filter(user=user).exists()
            if has_orders:
                raise CouponError("This coupon is valid for first orders only.")

        return coupon

    @staticmethod
    def calculate_discount(coupon, user, subtotal: Decimal, items) -> Decimal:
        """
        Calculate the actual discount amount for a given cart.
        """
        from .models import Coupon

        if coupon.discount_type == Coupon.DiscountType.FLAT:
            discount = coupon.discount_value
        else:
            discount = (subtotal * coupon.discount_value / Decimal("100")).quantize(Decimal("0.01"))
            if coupon.max_discount_cap:
                discount = min(discount, coupon.max_discount_cap)

        # Don't discount more than the subtotal
        return min(discount, subtotal)
