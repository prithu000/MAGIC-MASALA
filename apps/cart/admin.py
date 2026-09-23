"""
apps/cart/admin.py
Full-featured Cart & CartItem administration with customer identification,
item breakdown, custom box contents display, and abandoned cart tracking.
"""

from decimal import Decimal
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin, TabularInline

from .models import Cart, CartItem


class CartItemInline(TabularInline):
    model = CartItem
    extra = 0
    can_delete = True
    fields = (
        "item_display",
        "quantity",
        "unit_price_display",
        "line_total_display",
        "added_at",
    )
    readonly_fields = (
        "item_display",
        "unit_price_display",
        "line_total_display",
        "added_at",
    )

    @admin.display(description="Product / Combo Details")
    def item_display(self, obj):
        if obj.product:
            var_label = f" — {obj.variant.size_label}" if obj.variant and obj.variant.size_label else ""
            cat = f" [{obj.product.category.name}]" if obj.product.category else ""
            return f"🌿 {obj.product.name}{var_label}{cat}"
        elif obj.fixed_combo:
            return f"🎁 Fixed Combo: {obj.fixed_combo.name} (₹{obj.fixed_combo.combo_price})"
        elif obj.custom_combo_selection:
            # Decode the 10-masala box items
            selection = obj.custom_combo_selection
            items_dict = selection.items_json or {}
            from apps.catalog.models import Product
            p_ids = [int(k) for k in items_dict.keys() if str(k).isdigit()]
            products = {p.id: p.name for p in Product.objects.filter(id__in=p_ids)}
            breakdown = [f"{products.get(int(pid), f'ID:{pid}')} ×{qty}" for pid, qty in items_dict.items()]
            summary_str = ", ".join(breakdown) if breakdown else "Items not configured"
            return format_html(
                '<div>'
                '<strong>📦 Custom 10-Masala Box:</strong>'
                '<div style="font-size:12px; color:#4b5563; margin-top:3px; line-height:1.4;">{}</div>'
                '</div>',
                summary_str
            )
        return "Unknown Item"

    @admin.display(description="Unit Price")
    def unit_price_display(self, obj):
        return f"₹{obj.unit_price:.2f}"

    @admin.display(description="Total")
    def line_total_display(self, obj):
        return f"₹{obj.line_total:.2f}"


@admin.register(Cart)
class CartAdmin(ModelAdmin):
    list_display = (
        "customer_display",
        "phone_display",
        "items_count_display",
        "total_value_display",
        "cart_preview_display",
        "cart_status_badge",
        "updated_at",
    )
    list_filter = (
        ("user", admin.EmptyFieldListFilter),
        "created_at",
        "updated_at",
    )
    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "user__profile__phone",
        "session_key",
    )
    readonly_fields = (
        "customer_info_panel",
        "items_count_display",
        "total_value_display",
        "cart_status_badge",
        "created_at",
        "updated_at",
    )
    inlines = [CartItemInline]
    date_hierarchy = "updated_at"
    actions = ["delete_empty_carts", "send_cart_recovery_email"]

    @admin.display(description="Customer / User")
    def customer_display(self, obj):
        if obj.user:
            name = f"{obj.user.first_name} {obj.user.last_name}".strip()
            display = name if name else obj.user.email
            return format_html(
                '<div style="display:flex; align-items:center; gap:6px;">'
                '<span style="background:#8B1E1E; color:#fff; border-radius:50%; width:22px; height:22px; display:inline-flex; align-items:center; justify-content:center; font-size:11px; font-weight:bold;">👤</span>'
                '<div><strong>{}</strong><br><span style="font-size:11px; color:#6b7280;">{}</span></div>'
                '</div>',
                display,
                obj.user.email
            )
        return format_html(
            '<div style="color:#6b7280; font-size:12px;">'
            '<span>🕵️ Guest Session</span><br>'
            '<span style="font-family:monospace; font-size:10px;">{}...</span>'
            '</div>',
            obj.session_key[:16] if obj.session_key else "No session"
        )

    @admin.display(description="Phone")
    def phone_display(self, obj):
        if obj.user and hasattr(obj.user, "profile") and obj.user.profile.phone:
            return obj.user.profile.phone
        return "—"

    @admin.display(description="Items in Cart")
    def items_count_display(self, obj):
        total_qty = sum(item.quantity for item in obj.items.all())
        unique_items = obj.items.count()
        if total_qty == 0:
            return mark_safe('<span style="color:#9ca3af;">Empty</span>')
        return format_html('<strong>{}</strong> items ({} types)', total_qty, unique_items)

    @admin.display(description="Cart Total")
    def total_value_display(self, obj):
        total_val = sum(item.line_total for item in obj.items.all())
        return format_html('<strong style="color:#8B1E1E; font-size:14px;">₹{}</strong>', f"{total_val:.2f}")

    @admin.display(description="Items Preview")
    def cart_preview_display(self, obj):
        items = list(obj.items.all()[:3])
        if not items:
            return "—"
        snippets = []
        for i in items:
            name = i.product.name if i.product else (i.fixed_combo.name if i.fixed_combo else "Custom 10-Box")
            snippets.append(f"{name} ({i.quantity}×)")
        extra = obj.items.count() - len(items)
        if extra > 0:
            snippets.append(f"+{extra} more")
        return ", ".join(snippets)

    @admin.display(description="Status")
    def cart_status_badge(self, obj):
        if not obj.items.exists():
            return mark_safe('<span style="background:#f3f4f6; color:#6b7280; padding:3px 8px; border-radius:12px; font-size:11px; font-weight:600;">Empty Cart</span>')
        
        diff = timezone.now() - obj.updated_at
        hours = diff.total_seconds() / 3600
        if hours < 2:
            return mark_safe('<span style="background:#dcfce7; color:#15803d; padding:3px 8px; border-radius:12px; font-size:11px; font-weight:600;">🟢 Active Now</span>')
        elif hours < 24:
            return format_html('<span style="background:#fef9c3; color:#a16207; padding:3px 8px; border-radius:12px; font-size:11px; font-weight:600;">🟡 Recent ({:.0f}h ago)</span>', hours)
        else:
            days = hours / 24
            return format_html('<span style="background:#fee2e2; color:#b91c1c; padding:3px 8px; border-radius:12px; font-size:11px; font-weight:600;">🔴 Abandoned ({:.0f}d ago)</span>', days)

    @admin.display(description="Customer Profile Details")
    def customer_info_panel(self, obj):
        if obj.user:
            profile = getattr(obj.user, "profile", None)
            phone = profile.phone if profile else "Not provided"
            joined = obj.user.date_joined.strftime("%d %b %Y")
            return format_html(
                '<div style="background:#fafafa; border:1px solid #e5e7eb; padding:12px 16px; border-radius:8px; display:flex; gap:24px; font-size:13px;">'
                '<div><strong>Name:</strong> {} {}</div>'
                '<div><strong>Email:</strong> {}</div>'
                '<div><strong>Phone:</strong> {}</div>'
                '<div><strong>Member Since:</strong> {}</div>'
                '</div>',
                obj.user.first_name, obj.user.last_name, obj.user.email, phone, joined
            )
        return format_html('<span style="color:#6b7280;">Guest customer — session token: {}</span>', obj.session_key)

    @admin.action(description="🧹 Delete Empty / Abandoned Carts with 0 items")
    def delete_empty_carts(self, request, queryset):
        deleted_count = 0
        for cart in queryset:
            if not cart.items.exists():
                cart.delete()
                deleted_count += 1
        self.message_user(request, f"Cleaned up {deleted_count} empty cart(s).")

    @admin.action(description="📧 Send Abandoned Cart Reminder to Registered Users")
    def send_cart_recovery_email(self, request, queryset):
        sent_count = 0
        from apps.core.email_service import send_email_from_settings
        for cart in queryset:
            if cart.user and cart.user.email and cart.items.exists():
                items_summary = ", ".join([str(i) for i in cart.items.all()[:4]])
                total_val = sum(i.line_total for i in cart.items.all())
                context = {
                    "customer_name": cart.user.first_name or "Spice Lover",
                    "cart_items": cart.items.all(),
                    "cart_total": total_val,
                    "items_summary": items_summary,
                }
                # Send reminder
                try:
                    send_email_from_settings(
                        to_email=cart.user.email,
                        subject="Your Mahila Udyog Magic Masala Cart is Waiting! 🌶️",
                        template_name="emails/abandoned_cart.html",
                        context=context,
                        email_type="abandoned_cart"
                    )
                    sent_count += 1
                except Exception:
                    pass
        self.message_user(request, f"Dispatched recovery reminder to {sent_count} user(s).")


@admin.register(CartItem)
class CartItemAdmin(ModelAdmin):
    list_display = ("item_name_display", "cart_customer", "quantity", "unit_price", "line_total", "added_at")
    list_filter = ("added_at",)
    search_fields = ("product__name", "cart__user__email", "cart__session_key")

    @admin.display(description="Item")
    def item_name_display(self, obj):
        return str(obj)

    @admin.display(description="Cart Owner")
    def cart_customer(self, obj):
        if obj.cart.user:
            return obj.cart.user.email
        return f"Guest: {obj.cart.session_key[:10]}..."
