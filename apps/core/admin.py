"""
apps/core/admin.py — SiteSettings admin registration.
"""

from django.contrib import admin
from solo.admin import SingletonModelAdmin
from unfold.admin import ModelAdmin

from .models import SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(SingletonModelAdmin, ModelAdmin):
    fieldsets = (
        (
            "Brand & Contact",
            {
                "fields": (
                    "brand_name",
                    "announcement_bar_text",
                    "announcement_bar_link",
                    "announcement_bar_active",
                    "support_phone",
                    "support_email",
                    "whatsapp_number",
                    "address",
                    "fssai_license_number",
                )
            },
        ),
        (
            "Legal, GST & Bank Details (Tax Invoicing)",
            {
                "fields": (
                    "legal_firm_name",
                    "firm_subtitle",
                    "gstin",
                    "manufacturer_address",
                    "manufacturer_state",
                    "manufacturer_state_code",
                    "invoice_phone",
                    "bank_name",
                    "bank_account_no",
                    "bank_ifsc_code",
                    "invoice_prefix",
                    "next_invoice_number",
                    "dispute_jurisdiction",
                ),
                "description": (
                    "Configure official registered manufacturing details for GST Tax Invoices. "
                    "These appear directly on generated PDF/Printable bills for GST Registration & Department Audits."
                ),
            },
        ),
        (
            "Social Media Links",
            {"fields": ("instagram_url", "facebook_url", "youtube_url", "twitter_url")},
        ),
        (
            "Order Rules",
            {
                "fields": (
                    "min_order_value",
                    "cod_charge",
                    "cod_advance_percent",
                    "free_shipping_threshold",
                ),
                "description": (
                    "These numbers control checkout calculations. "
                    "Changes take effect immediately — no redeploy needed."
                ),
            },
        ),
        (
            "Combo Rules",
            {
                "fields": (
                    "fixed_combo_item_count",
                    "customize_combo_item_count",
                    "customize_combo_max_units_per_product",
                    "customize_combo_price",
                ),
                "description": (
                    "Control how many items customers must select to complete a Build-Your-Own combo (e.g. 10), "
                    "max quantity per individual product (e.g. max 2 of any single spice), and flat price (e.g. ₹999). "
                    "Updating here automatically updates the active combo rule."
                ),
            },
        ),
        (
            "Default SEO & Open Graph",
            {"fields": ("meta_title", "meta_description", "og_image")},
        ),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        try:
            from apps.combos.models import CustomizeComboRule
            rule = CustomizeComboRule.objects.filter(is_active=True).first()
            if rule:
                rule.required_item_count = obj.customize_combo_item_count
                rule.max_units_per_product = obj.customize_combo_max_units_per_product
                if obj.customize_combo_price:
                    rule.fixed_price = obj.customize_combo_price
                rule.save(update_fields=["required_item_count", "max_units_per_product", "fixed_price"])
        except Exception:
            pass


from django.contrib import messages
from django.urls import path, reverse
from django.utils.html import format_html
from django.shortcuts import redirect

from .models import EmailSettings, EmailCampaign, EmailLog
from .email_service import send_test_email, broadcast_campaign


@admin.register(EmailSettings)
class EmailSettingsAdmin(SingletonModelAdmin, ModelAdmin):
    readonly_fields = ("test_connection_panel",)

    fieldsets = (
        (
            "Diagnostics & Live Test",
            {
                "fields": ("test_connection_panel",),
                "description": "Verify your Brevo SMTP connection and send a test email to your admin address.",
            },
        ),
        (
            "Master Switch",
            {
                "fields": ("is_enabled",),
                "description": "Turn all outgoing automated and marketing emails ON or OFF.",
            },
        ),
        (
            "Brevo SMTP Relay Credentials",
            {
                "fields": (
                    "smtp_host",
                    "smtp_port",
                    "smtp_use_tls",
                    "smtp_user",
                    "smtp_password",
                ),
                "description": (
                    "Direct Brevo SMTP connection. You can change credentials or Brevo login email "
                    "directly here without touching server configuration."
                ),
            },
        ),
        (
            "Sender & Support Identity",
            {
                "fields": ("from_name", "from_email", "support_email", "support_phone"),
                "description": "Branding, display name, and reply-to details appearing in customer inboxes.",
            },
        ),
        (
            "Welcome Email (New Customer Registration)",
            {
                "fields": ("welcome_email_enabled", "welcome_email_subject", "welcome_coupon_code"),
                "description": "Triggered when a new user registers on the website.",
            },
        ),
        (
            "Order Confirmation Email",
            {
                "fields": ("order_confirmation_enabled", "order_confirmation_subject"),
                "description": "Itemized bill & receipt dispatched immediately upon payment/order placement.",
            },
        ),
        (
            "Order Status & Delivery Updates",
            {
                "fields": ("order_status_update_enabled", "order_status_subject"),
                "description": "Sent when order status changes to Packed, Shipped, Out for Delivery, or Delivered.",
            },
        ),
        (
            "Security Alerts & Cart Reminders",
            {
                "fields": (
                    "password_change_enabled",
                    "password_change_subject",
                    "abandoned_cart_enabled",
                    "abandoned_cart_subject",
                ),
            },
        ),
        (
            "Email Footer & Legal Reassurance",
            {
                "fields": ("footer_text",),
            },
        ),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "test-brevo/",
                self.admin_site.admin_view(self.test_brevo_view),
                name="emailsettings_test_brevo",
            ),
        ]
        return custom_urls + urls

    def test_brevo_view(self, request):
        if request.method != "POST":
            messages.error(request, "Invalid request method. POST required.")
            return redirect(reverse("admin:core_emailsettings_change"))

        target_email = (request.POST.get("test_brevo_to") or request.POST.get("to") or request.user.email or "").strip()
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        try:
            validate_email(target_email)
        except ValidationError:
            messages.error(request, "Please provide a valid recipient email address.")
            return redirect(reverse("admin:core_emailsettings_change"))

        try:
            send_test_email(target_email)
            messages.success(
                request,
                f"⚡ Test email successfully dispatched to {target_email} via Brevo SMTP!",
            )
        except Exception as e:
            messages.error(
                request,
                f"Failed to deliver test email via Brevo: {e}",
            )
        return redirect(reverse("admin:core_emailsettings_change"))

    def test_connection_panel(self, obj):
        url = reverse("admin:emailsettings_test_brevo")
        logs_url = reverse("admin:core_emaillog_changelist")
        campaigns_url = reverse("admin:core_emailcampaign_changelist")
        return format_html(
            '<div style="background:#fffbeb; border:1.5px solid #f59e0b; padding:18px 22px; border-radius:12px; display:flex; flex-direction:column; gap:14px;">'
            '<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">'
            '<div>'
            '<strong style="color:#92400e; font-size:15px; display:block; margin-bottom:3px;">⚡ Brevo SMTP Live Test & Diagnostics</strong>'
            '<span style="color:#78350f; font-size:13px;">Test your email relay directly to any inbox to verify DKIM, SPF and live delivery.</span>'
            '</div>'
            '<div style="display:flex; gap:14px; font-size:12px;">'
            '<a href="{}" style="color:#b45309; font-weight:700; text-decoration:underline;">📋 View Email Delivery Logs</a>'
            '<a href="{}" style="color:#b45309; font-weight:700; text-decoration:underline;">🚀 Marketing Campaigns</a>'
            '</div>'
            '</div>'
            '<div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">'
            '<input type="email" name="test_brevo_to" value="Mahilaudyogmagic@gmail.com" placeholder="Recipient email address" style="padding:9px 14px; border:1px solid #d1d5db; border-radius:6px; font-size:13px; min-width:280px; flex:1; max-width:400px; background:#ffffff; color:#111827;">'
            '<button type="submit" formaction="{}" formmethod="POST" style="background:#d97706; color:#ffffff; padding:9px 20px; border-radius:6px; font-weight:700; border:none; cursor:pointer; font-size:13px; box-shadow:0 2px 4px rgba(217,119,6,0.3); display:inline-flex; align-items:center; gap:6px;">🚀 Send Diagnostic Test Email</button>'
            '</div>'
            '</div>',
            logs_url,
            campaigns_url,
            url,
        )

    test_connection_panel.short_description = "Live SMTP Test"


@admin.register(EmailCampaign)
class EmailCampaignAdmin(ModelAdmin):
    list_display = (
        "title",
        "subject",
        "coupon_code",
        "discount_highlight",
        "status",
        "recipients_sent",
        "sent_at",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("title", "subject", "heading", "coupon_code")
    readonly_fields = ("recipients_sent", "sent_at", "created_at")

    fieldsets = (
        (
            "Campaign Details",
            {
                "fields": ("title", "subject", "preview_text", "status"),
            },
        ),
        (
            "Creative Header & Visuals",
            {
                "fields": ("badge_text", "heading", "subheading", "banner_image_url"),
            },
        ),
        (
            "Offer Content & Voucher",
            {
                "fields": ("message_body", "coupon_code", "discount_highlight"),
                "description": "Display a beautiful discount voucher badge with copyable coupon code.",
            },
        ),
        (
            "Call to Action Button",
            {
                "fields": ("cta_text", "cta_url"),
            },
        ),
        (
            "Delivery Statistics",
            {
                "fields": ("recipients_sent", "sent_at", "created_at"),
            },
        ),
    )

    actions = ["send_test_campaign_action", "broadcast_campaign_action"]

    @admin.action(description="📨 Send Test Email of this Campaign to Admin")
    def send_test_campaign_action(self, request, queryset):
        target_email = request.user.email or "care@mumagicmasala.com"
        count = 0
        for campaign in queryset:
            broadcast_campaign(campaign, test_email=target_email)
            count += 1
        self.message_user(
            request,
            f"Test preview of {count} campaign(s) sent to {target_email}.",
            level=messages.SUCCESS,
        )

    @admin.action(description="🚀 Broadcast Campaign to ALL Registered Customers")
    def broadcast_campaign_action(self, request, queryset):
        total_sent = 0
        for campaign in queryset:
            sent_count = broadcast_campaign(campaign)
            total_sent += sent_count
        self.message_user(
            request,
            f"Broadcast initiated! {total_sent} customer email(s) queued for delivery.",
            level=messages.SUCCESS,
        )


@admin.register(EmailLog)
class EmailLogAdmin(ModelAdmin):
    list_display = ("created_at", "email_type", "recipient", "subject", "status")
    list_filter = ("status", "email_type", "created_at")
    search_fields = ("recipient", "subject", "error_message")
    readonly_fields = ("created_at", "email_type", "recipient", "subject", "status", "error_message")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

