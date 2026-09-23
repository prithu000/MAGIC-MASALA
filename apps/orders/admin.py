"""
apps/orders/admin.py
"""

from decimal import Decimal
from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin, StackedInline, TabularInline

from .invoice_service import get_or_generate_tax_invoice
from .models import Order, OrderItem, OrderStatusHistory


class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    fields = (
        "product",
        "item_name",
        "hsn_code",
        "quantity",
        "price_at_purchase",
        "taxable_value",
        "gst_rate",
        "cgst_amount",
        "sgst_amount",
        "igst_amount",
        "line_total",
    )
    readonly_fields = (
        "taxable_value",
        "cgst_amount",
        "sgst_amount",
        "igst_amount",
        "line_total",
    )
    can_delete = True


class OrderStatusHistoryInline(TabularInline):
    model = OrderStatusHistory
    extra = 1
    readonly_fields = ("timestamp",)
    fields = ("status", "note", "timestamp")


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = (
        "order_number",
        "invoice_number",
        "user",
        "total",
        "payment_method",
        "payment_status",
        "order_status",
        "created_at",
        "tax_invoice_link",
    )
    list_filter = ("order_status", "payment_method", "payment_status", "is_interstate", "created_at")
    search_fields = (
        "order_number",
        "invoice_number",
        "customer_gstin",
        "user__email",
        "shipping_full_name",
        "shipping_phone",
    )
    readonly_fields = (
        "order_number",
        "customer_email_actions_display",
        "subtotal",
        "discount_amount",
        "cod_charge_applied",
        "total",
        "advance_amount",
        "remaining_amount",
        "taxable_amount",
        "cgst_amount",
        "sgst_amount",
        "igst_amount",
        "tax_invoice_button_display",
        "created_at",
        "updated_at",
    )
    inlines = [OrderItemInline, OrderStatusHistoryInline]
    date_hierarchy = "created_at"
    save_on_top = True
    actions = [
        "generate_tax_invoices_action",
        "resend_order_confirmations_action",
        "send_status_updates_action",
    ]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:order_id>/tax-invoice/",
                self.admin_site.admin_view(self.tax_invoice_view),
                name="order_tax_invoice",
            ),
            path(
                "<int:order_id>/send-confirmation-email/",
                self.admin_site.admin_view(self.send_confirmation_email_view),
                name="order_send_confirmation_email",
            ),
            path(
                "<int:order_id>/send-status-email/",
                self.admin_site.admin_view(self.send_status_email_view),
                name="order_send_status_email",
            ),
        ]
        return custom_urls + urls

    def send_confirmation_email_view(self, request, order_id):
        if request.method != "POST":
            self.message_user(request, "Invalid request method. POST required.", level=messages.ERROR)
            return redirect(reverse("admin:orders_order_change", args=[order_id]))
        order = get_object_or_404(Order, pk=order_id)
        from apps.core.email_service import send_order_confirmation_email
        try:
            send_order_confirmation_email(order)
            self.message_user(
                request,
                f"✅ Order confirmation & bill dispatched to {order.user.email if order.user else 'customer'}!",
                level=messages.SUCCESS
            )
        except Exception as e:
            self.message_user(request, f"❌ Failed to dispatch email: {e}", level=messages.ERROR)
        return redirect(reverse("admin:orders_order_change", args=[order_id]))

    def send_status_email_view(self, request, order_id):
        if request.method != "POST":
            self.message_user(request, "Invalid request method. POST required.", level=messages.ERROR)
            return redirect(reverse("admin:orders_order_change", args=[order_id]))
        order = get_object_or_404(Order, pk=order_id)
        from apps.core.email_service import send_order_status_update_email
        try:
            send_order_status_update_email(order, order.get_order_status_display(), order.order_status)
            self.message_user(
                request,
                f"✅ Delivery status update email ({order.get_order_status_display()}) dispatched!",
                level=messages.SUCCESS
            )
        except Exception as e:
            self.message_user(request, f"❌ Failed to dispatch status update email: {e}", level=messages.ERROR)
        return redirect(reverse("admin:orders_order_change", args=[order_id]))

    @admin.action(description="📧 Resend Order Confirmation & Bill via Brevo")
    def resend_order_confirmations_action(self, request, queryset):
        from apps.core.email_service import send_order_confirmation_email
        count = 0
        for order in queryset:
            try:
                send_order_confirmation_email(order)
                count += 1
            except Exception:
                pass
        self.message_user(request, f"Successfully dispatched order confirmation bills to {count} customer(s).")

    @admin.action(description="🚚 Send Delivery Status Update Email to Customers")
    def send_status_updates_action(self, request, queryset):
        from apps.core.email_service import send_order_status_update_email
        count = 0
        for order in queryset:
            try:
                send_order_status_update_email(order, order.get_order_status_display(), order.order_status)
                count += 1
            except Exception:
                pass
        self.message_user(request, f"Successfully dispatched status updates to {count} customer(s).")

    def customer_email_actions_display(self, obj):
        if not obj or not obj.pk:
            return "Save order first to dispatch customer emails."
        recipient = obj.user.email if obj.user else (obj.shipping_phone or "No email linked")
        conf_url = reverse("admin:order_send_confirmation_email", args=[obj.pk])
        status_url = reverse("admin:order_send_status_email", args=[obj.pk])
        return format_html(
            '<div style="background:#fff7ed; border:1.5px solid #fdba74; padding:14px 18px; border-radius:10px; display:flex; flex-direction:column; gap:10px;">'
            '<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">'
            '<div style="font-size:13px; color:#9a3412;">'
            '<strong>Recipient:</strong> <code style="background:#ffffff; padding:2px 6px; border-radius:4px; font-weight:700;">{}</code> &bull; Status: <span style="background:#8B1E1E; color:#fff; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:700;">{}</span>'
            '</div>'
            '</div>'
            '<div style="display:flex; gap:10px; flex-wrap:wrap;">'
            '<button type="submit" formaction="{}" formmethod="POST" style="background:#8B1E1E; color:#ffffff; padding:7px 16px; border-radius:6px; font-weight:700; border:none; cursor:pointer; font-size:12px; display:inline-flex; align-items:center; gap:6px; box-shadow:0 2px 4px rgba(139,30,30,0.25);">📧 Send Confirmation & Bill</button>'
            '<button type="submit" formaction="{}" formmethod="POST" style="background:#d97706; color:#ffffff; padding:7px 16px; border-radius:6px; font-weight:700; border:none; cursor:pointer; font-size:12px; display:inline-flex; align-items:center; gap:6px; box-shadow:0 2px 4px rgba(217,119,6,0.25);">🚚 Send Status Update Email</button>'
            '</div>'
            '</div>',
            recipient,
            obj.get_order_status_display(),
            conf_url,
            status_url,
        )

    customer_email_actions_display.short_description = "Customer Email Dispatch (Brevo)"

    def tax_invoice_view(self, request, order_id):
        order = get_object_or_404(Order, pk=order_id)
        force = request.GET.get("recalculate") == "1"
        context = get_or_generate_tax_invoice(order, force_regenerate=force)
        return render(request, "admin/orders/tax_invoice.html", context)

    def tax_invoice_link(self, obj):
        if not obj.pk:
            return "-"
        url = reverse("admin:order_tax_invoice", args=[obj.pk])
        label = f"📄 Bill {obj.invoice_number}" if obj.invoice_number else "📄 Generate Bill"
        return format_html(
            '<a href="{}" target="_blank" style="background:#0f3460; color:#ffffff; padding:4px 10px; border-radius:4px; font-weight:700; text-decoration:none; font-size:12px; display:inline-block; box-shadow:0 1px 2px rgba(0,0,0,0.15);">{}</a>',
            url,
            label,
        )

    tax_invoice_link.short_description = "Tax Invoice"

    def tax_invoice_button_display(self, obj):
        if not obj.pk:
            return "Save order first to generate invoice."
        url = reverse("admin:order_tax_invoice", args=[obj.pk])
        recalc_url = f"{url}?recalculate=1"
        invoice_num = obj.invoice_number or "Not Assigned Yet"
        return format_html(
            '<div style="background:#f8fafc; border:1px solid #cbd5e1; padding:12px 16px; border-radius:6px; display:inline-flex; align-items:center; gap:16px;">'
            '<div><strong>Official Invoice:</strong> <span style="font-family:monospace; font-weight:700; color:#0f3460;">{}</span></div>'
            '<a href="{}" target="_blank" style="background:#0f3460; color:#fff; padding:7px 14px; border-radius:4px; text-decoration:none; font-weight:700; font-size:13px;">🖨️ View / Print Tax Invoice</a>'
            '<a href="{}" target="_blank" style="background:#475569; color:#fff; padding:7px 14px; border-radius:4px; text-decoration:none; font-weight:600; font-size:13px;">🔄 Recalculate Taxes</a>'
            '</div>',
            invoice_num,
            url,
            recalc_url,
        )

    tax_invoice_button_display.short_description = "GST Tax Invoice Actions"

    @admin.action(description="Generate official GST Tax Invoices for selected orders")
    def generate_tax_invoices_action(self, request, queryset):
        count = 0
        for order in queryset:
            get_or_generate_tax_invoice(order)
            count += 1
        self.message_user(request, f"Successfully processed GST Tax Invoices for {count} order(s).")

    def save_model(self, request, obj, form, change):
        if not change:
            if not obj.subtotal:
                obj.subtotal = Decimal("0.00")
            if not obj.shipping_charge:
                obj.shipping_charge = Decimal("0.00")
            if not obj.total:
                obj.total = (
                    obj.subtotal
                    + (obj.shipping_charge or Decimal("0.00"))
                    + (obj.cod_charge_applied or Decimal("0.00"))
                    - (obj.discount_amount or Decimal("0.00"))
                )
            if obj.payment_method == "cod" and not obj.advance_amount and obj.total > 0:
                try:
                    from apps.core.models import SiteSettings
                    settings = SiteSettings.get_solo()
                    pct = settings.cod_advance_percent or Decimal("10.00")
                    obj.advance_amount = (obj.total * pct / Decimal("100")).quantize(Decimal("0.01"))
                    obj.remaining_amount = obj.total - obj.advance_amount
                except Exception:
                    pass
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        obj = form.instance
        items = obj.items.all()
        if items.exists():
            item_subtotal = sum(item.line_total for item in items if item.line_total)
            if item_subtotal > 0:
                obj.subtotal = item_subtotal
                obj.total = (
                    obj.subtotal
                    + (obj.shipping_charge or Decimal("0.00"))
                    + (obj.cod_charge_applied or Decimal("0.00"))
                    - (obj.discount_amount or Decimal("0.00"))
                )
                if obj.payment_method == "cod":
                    try:
                        from apps.core.models import SiteSettings
                        settings = SiteSettings.get_solo()
                        pct = settings.cod_advance_percent or Decimal("10.00")
                        obj.advance_amount = (obj.total * pct / Decimal("100")).quantize(Decimal("0.01"))
                        obj.remaining_amount = obj.total - obj.advance_amount
                    except Exception:
                        pass
                obj.save(update_fields=["subtotal", "total", "advance_amount", "remaining_amount"])

    fieldsets = (
        (
            "Customer Email Dispatch (Brevo)",
            {
                "fields": ("customer_email_actions_display",),
                "description": "Send or re-send official order confirmation bill and live delivery updates directly to the customer's inbox.",
            },
        ),
        (
            "Tax Invoice & Legal GST (Mahila Udhyog)",
            {
                "fields": (
                    "tax_invoice_button_display",
                    "invoice_number",
                    "invoice_date",
                    "customer_gstin",
                    "place_of_supply",
                    "is_interstate",
                    "transport_mode",
                    "vehicle_number",
                    "taxable_amount",
                    "cgst_amount",
                    "sgst_amount",
                    "igst_amount",
                ),
                "description": "Official Mahila Udhyog tax invoice record matching the physical bill book for GST department registration & filing.",
            },
        ),
        (
            "Order Info",
            {"fields": ("order_number", "user", "created_at", "updated_at")},
        ),
        (
            "Shipping Address",
            {
                "fields": (
                    "shipping_full_name",
                    "shipping_phone",
                    "shipping_address_line1",
                    "shipping_address_line2",
                    "shipping_landmark",
                    "shipping_city",
                    "shipping_state",
                    "shipping_pincode",
                )
            },
        ),
        (
            "Financials",
            {
                "fields": (
                    "subtotal",
                    "discount_amount",
                    "cod_charge_applied",
                    "shipping_charge",
                    "total",
                    "coupon_code",
                )
            },
        ),
        (
            "Payment",
            {
                "fields": (
                    "payment_method",
                    "payment_status",
                    "advance_amount",
                    "remaining_amount",
                )
            },
        ),
        (
            "Order Status & Tracking",
            {"fields": ("order_status", "tracking_number", "courier_name")},
        ),
    )


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(ModelAdmin):
    list_display = ("order", "status", "timestamp")
    list_filter = ("status",)
    readonly_fields = ("timestamp",)
