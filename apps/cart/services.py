"""
apps/cart/services.py
CartService — the single class all views use to touch the cart.
All business calculations read from SiteSettings at call time.
"""

from decimal import Decimal

from django.db import transaction

from apps.core.models import SiteSettings
from apps.coupons.services import CouponService, CouponError

from .models import Cart, CartItem


class CartService:

    @staticmethod
    def get_or_create_cart(request) -> Cart:
        """Return the cart for the current user/session, creating it if needed."""
        if request.user.is_authenticated:
            cart, _ = Cart.objects.get_or_create(user=request.user)
            # Merge any guest cart from the session
            CartService._merge_session_cart(request, cart)
            return cart
        else:
            if not request.session.session_key:
                request.session.create()
            cart, _ = Cart.objects.get_or_create(session_key=request.session.session_key, user=None)
            return cart

    @staticmethod
    def _merge_session_cart(request, user_cart: Cart):
        """After login, merge the session cart into the authenticated cart."""
        session_key = request.session.session_key
        if not session_key:
            return
        try:
            guest_cart = Cart.objects.get(session_key=session_key, user=None)
        except Cart.DoesNotExist:
            return

        with transaction.atomic():
            for item in guest_cart.items.all():
                existing = user_cart.items.filter(
                    product=item.product,
                    variant=item.variant,
                ).first()
                if existing:
                    existing.quantity += item.quantity
                    existing.save()
                else:
                    item.cart = user_cart
                    item.save()
            guest_cart.delete()

    @staticmethod
    def add_item(request, product_id=None, variant_id=None, combo_id=None,
                 custom_combo_id=None, quantity=1) -> CartItem:
        from apps.catalog.models import Product, ProductVariant
        from apps.combos.models import FixedCombo, CustomComboSelection

        # Sanitize and clamp quantity (prevent negative/zero/excessive quantities)
        try:
            quantity = max(1, min(int(quantity), 50))
        except (ValueError, TypeError):
            quantity = 1

        cart = CartService.get_or_create_cart(request)

        if product_id:
            product = Product.objects.get(pk=product_id, is_active=True)
            if variant_id:
                # Security: prevent BOLA/IDOR by ensuring variant belongs strictly to this product
                try:
                    variant = ProductVariant.objects.get(pk=variant_id, product=product, is_active=True)
                except ProductVariant.DoesNotExist:
                    raise ValueError("Specified variant does not belong to this product or is inactive.")
            else:
                variant = None
            item, created = cart.items.get_or_create(
                product=product,
                variant=variant,
                fixed_combo=None,
                custom_combo_selection=None,
                defaults={"quantity": quantity},
            )
            if not created:
                item.quantity = min(50, item.quantity + quantity)
                item.save()
        elif combo_id:
            combo = FixedCombo.objects.get(pk=combo_id, is_active=True)
            item, created = cart.items.get_or_create(
                fixed_combo=combo,
                product=None,
                custom_combo_selection=None,
                defaults={"quantity": quantity},
            )
            if not created:
                item.quantity = min(50, item.quantity + quantity)
                item.save()
        elif custom_combo_id:
            selection = CustomComboSelection.objects.get(pk=custom_combo_id, is_complete=True)
            # Ownership check to prevent IDOR attaching another user's combo
            if selection.user and request.user.is_authenticated and selection.user != request.user:
                raise ValueError("Unauthorized custom combo selection")
            if not selection.user and selection.session_key and request.session.session_key and selection.session_key != request.session.session_key:
                raise ValueError("Unauthorized custom combo selection")
            item = cart.items.create(custom_combo_selection=selection, quantity=min(quantity, 10))

        return item

    @staticmethod
    def update_item(request, item_id: int, quantity: int) -> CartItem | None:
        cart = CartService.get_or_create_cart(request)
        try:
            item = cart.items.get(pk=item_id)
            try:
                quantity = int(quantity)
            except (ValueError, TypeError):
                quantity = 1

            if quantity <= 0:
                item.delete()
                return None
            # Clamp maximum quantity per item to 50
            item.quantity = min(50, quantity)
            item.save()
            return item
        except CartItem.DoesNotExist:
            return None

    @staticmethod
    def remove_item(request, item_id: int):
        cart = CartService.get_or_create_cart(request)
        cart.items.filter(pk=item_id).delete()

    @staticmethod
    def compute_totals(request, payment_method: str = "online") -> dict:
        """
        Compute all cart totals reading from SiteSettings.
        Returns a dict used by templates and checkout views.
        """
        settings = SiteSettings.get_solo()
        cart = CartService.get_or_create_cart(request)
        # Purge any cart items referencing deactivated products, variants, or combos
        raw_items = list(cart.items.select_related("product", "variant", "fixed_combo", "custom_combo_selection").all())
        items = []
        for item in raw_items:
            if item.product and (not item.product.is_active or (item.variant and not item.variant.is_active)):
                item.delete()
                continue
            if item.fixed_combo and not item.fixed_combo.is_active:
                item.delete()
                continue
            items.append(item)

        subtotal = sum(item.line_total for item in items)

        # Coupon discount
        discount = Decimal("0.00")
        coupon = cart.coupon
        coupon_error = None
        if coupon:
            try:
                discount = CouponService.calculate_discount(coupon, request.user, subtotal, items)
            except CouponError as e:
                coupon_error = str(e)
                cart.coupon = None
                cart.save()
                coupon = None

        subtotal_after_discount = max(Decimal("0.00"), subtotal - discount)

        # 5% GST on spices
        tax_amount = (subtotal_after_discount * Decimal("0.05")).quantize(Decimal("0.01"))

        # Shipping: Free above threshold (₹499), otherwise ₹49 flat
        shipping = Decimal("0.00")
        free_shipping = False
        if items:
            if settings.free_shipping_threshold and subtotal_after_discount >= settings.free_shipping_threshold:
                free_shipping = True
            elif settings.free_shipping_threshold:
                shipping = Decimal("49.00")

        # COD charge
        cod_charge = Decimal("0.00")
        if payment_method == "cod":
            cod_charge = settings.cod_charge

        total = subtotal_after_discount + tax_amount + shipping + cod_charge

        # COD advance calculation
        cod_advance = Decimal("0.00")
        cod_remaining = Decimal("0.00")
        if payment_method == "cod":
            cod_advance = settings.compute_cod_advance(total - cod_charge)
            cod_remaining = settings.compute_cod_remaining(total - cod_charge)

        # Shortfall to minimum order
        shortfall = max(Decimal("0.00"), settings.min_order_value - subtotal_after_discount) if items else Decimal("0.00")
        meets_minimum = (shortfall == 0) and bool(items)

        # Shortfall to free shipping
        shipping_shortfall = Decimal("0.00")
        if settings.free_shipping_threshold and not free_shipping and items:
            shipping_shortfall = max(Decimal("0.00"), settings.free_shipping_threshold - subtotal_after_discount)

        return {
            "cart": cart,
            "items": items,
            "subtotal": subtotal,
            "discount": discount,
            "coupon": coupon,
            "coupon_error": coupon_error,
            "subtotal_after_discount": subtotal_after_discount,
            "gst_rate": Decimal("5"),
            "tax_amount": tax_amount,
            "shipping": shipping,
            "free_shipping": free_shipping,
            "cod_charge": cod_charge,
            "total": total,
            "cod_advance": cod_advance,
            "cod_remaining": cod_remaining,
            "shortfall": shortfall,
            "meets_minimum": meets_minimum,
            "shipping_shortfall": shipping_shortfall,
            "min_order_value": settings.min_order_value,
            "free_shipping_threshold": settings.free_shipping_threshold,
        }
