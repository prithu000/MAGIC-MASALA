"""
apps/accounts/admin.py
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from unfold.admin import ModelAdmin, StackedInline

from .models import Address, CustomerProfile, Wishlist


class CustomerProfileInline(StackedInline):
    model = CustomerProfile
    can_delete = False
    verbose_name_plural = "Profile"


class AddressInline(StackedInline):
    model = Address
    extra = 0


admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(UserAdmin, ModelAdmin):
    inlines = [CustomerProfileInline, AddressInline]


@admin.register(CustomerProfile)
class CustomerProfileAdmin(ModelAdmin):
    list_display = ("user", "phone", "cart_details_display", "admin_avatar")
    search_fields = ("user__email", "user__first_name", "user__last_name", "phone")
    raw_id_fields = ("user",)

    @admin.display(description="Active Cart")
    def cart_details_display(self, obj):
        from django.utils.html import format_html
        from django.urls import reverse
        cart = getattr(obj.user, "cart", None)
        if cart and cart.items.exists():
            count = sum(i.quantity for i in cart.items.all())
            total = sum(i.line_total for i in cart.items.all())
            url = reverse("admin:cart_cart_change", args=[cart.id])
            return format_html(
                '<a href="{}" style="font-weight:700; color:#8B1E1E;">🛒 {} items (₹{:.0f})</a>',
                url, count, total
            )
        return format_html('<span style="color:#9ca3af;">Empty</span>')

    @admin.display(description="Avatar")
    def admin_avatar(self, obj):
        if obj.avatar:
            from django.utils.html import format_html
            return format_html('<img src="{}" style="width:36px;height:36px;border-radius:50%;object-fit:cover;" />', obj.avatar.url)
        return "No Avatar"


@admin.register(Address)
class AddressAdmin(ModelAdmin):
    list_display = ("user", "full_name", "city", "state", "pincode", "is_default")
    list_filter = ("state", "is_default", "address_type")
    search_fields = ("user__email", "full_name", "pincode")


@admin.register(Wishlist)
class WishlistAdmin(ModelAdmin):
    list_display = ("user", "product", "added_at")
    list_filter = ("added_at",)
    raw_id_fields = ("user", "product")

