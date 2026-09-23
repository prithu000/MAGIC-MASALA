"""
apps/core/models.py — SiteSettings singleton.
All admin-editable business rules live here. Nothing from Section 4 of the
spec is hardcoded elsewhere; every checkout calculation reads from this object.
"""

from decimal import Decimal

from django.db import models
from solo.models import SingletonModel


class SiteSettings(SingletonModel):
    """
    Singleton model for all site-wide business rules.
    Owner edits these from Admin → Settings → Site Settings.
    """

    # ------------------------------------------------------------------
    # Brand & Contact
    # ------------------------------------------------------------------
    brand_name = models.CharField(max_length=120, default="MAGIC MASALA")
    announcement_bar_text = models.CharField(
        max_length=255,
        default="AUTHENTIC INDIAN MASALAS • FREE SHIPPING ABOVE ₹499",
        blank=True,
    )
    announcement_bar_link = models.CharField(max_length=255, blank=True, default="/combos/")
    announcement_bar_active = models.BooleanField(default=True)
    support_phone = models.CharField(max_length=20, blank=True)
    support_email = models.EmailField(blank=True)
    whatsapp_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="Include country code, e.g. +919876543210",
    )
    address = models.TextField(blank=True)

    # ------------------------------------------------------------------
    # Legal & GST Billing Information (Mahila Udhyog)
    # ------------------------------------------------------------------
    legal_firm_name = models.CharField(
        max_length=150,
        default="Mahila Udhyog",
        help_text="Official registered business entity name printed on tax invoices.",
    )
    firm_subtitle = models.CharField(
        max_length=200,
        default="Wholesale & Retail : Kirana & Spice Manufacturers",
        help_text="Business description line printed below firm name on invoice.",
        blank=True,
    )
    gstin = models.CharField(
        max_length=20,
        default="09ALVPP8219Q1ZW",
        help_text="15-digit Goods and Services Tax Identification Number (State Code 09 = UP).",
        blank=True,
    )
    manufacturer_address = models.CharField(
        max_length=255,
        default="Chitragupta Colony, Gali No.3, Kasganj- 207123",
        help_text="Registered manufacturing factory and office address.",
        blank=True,
    )
    manufacturer_state = models.CharField(
        max_length=60,
        default="Uttar Pradesh",
        help_text="State of supplier (determines CGST+SGST vs IGST).",
    )
    manufacturer_state_code = models.CharField(
        max_length=5,
        default="09",
        help_text="2-digit GST state code (09 for Uttar Pradesh).",
    )
    invoice_phone = models.CharField(
        max_length=25,
        default="7805105024",
        help_text="Contact number printed on invoices.",
        blank=True,
    )
    bank_name = models.CharField(
        max_length=120,
        default="BANK OF BARODA, KASGANJ",
        help_text="Bank and branch name for NEFT/RTGS/IMPS customer payments.",
        blank=True,
    )
    bank_account_no = models.CharField(
        max_length=40,
        default="27270200000665",
        help_text="Bank Account Number printed on invoices.",
        blank=True,
    )
    bank_ifsc_code = models.CharField(
        max_length=20,
        default="BARB0BLYKNJ",
        help_text="Bank IFSC code for electronic settlements.",
        blank=True,
    )
    invoice_prefix = models.CharField(
        max_length=20,
        default="MU/26-27/",
        help_text="Series prefix for sequential Tax Invoices (e.g. MU/26-27/).",
    )
    next_invoice_number = models.PositiveIntegerField(
        default=81,
        help_text="Next sequential invoice serial number (as in bill book).",
    )
    dispute_jurisdiction = models.CharField(
        max_length=80,
        default="KASGANJ",
        help_text="Jurisdiction town for legal dispute clause (e.g. KASGANJ).",
    )

    # ------------------------------------------------------------------
    # Social links
    # ------------------------------------------------------------------
    instagram_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)

    # ------------------------------------------------------------------
    # Order rules
    # ------------------------------------------------------------------
    min_order_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("199.00"),
        help_text="Checkout is blocked below this amount. Customer sees the shortfall.",
    )
    cod_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Extra delivery fee added to the order total when customer selects Cash on Delivery.",
    )
    cod_advance_mode = models.CharField(
        max_length=10,
        choices=[("fixed", "Fixed Amount"), ("percent", "Percentage")],
        default="fixed",
    )
    cod_advance_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("59.00"),
        help_text="Fixed upfront advance payment collected online when choosing COD.",
    )
    cod_advance_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("50.00"),
        help_text="Percentage of order customer pays upfront if percent mode is selected (0–100).",
    )
    free_shipping_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("499.00"),
        null=True,
        blank=True,
        help_text="Leave blank to disable free shipping. When set, orders above this amount ship free.",
    )

    # ------------------------------------------------------------------
    # Combo rules
    # ------------------------------------------------------------------
    fixed_combo_item_count = models.PositiveSmallIntegerField(
        default=5,
        help_text="Number of items in a fixed (pre-built) combo.",
    )
    customize_combo_item_count = models.PositiveSmallIntegerField(
        default=10,
        help_text="Number of items a customer must pick to complete a Build-Your-Own combo.",
    )
    customize_combo_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("999.00"),
        help_text="Fixed price charged for a completed Build-Your-Own 10-masala combo.",
    )
    customize_combo_max_units_per_product = models.PositiveSmallIntegerField(
        default=2,
        help_text="Maximum quantity of any single product allowed in the Build-Your-Own combo.",
    )

    # ------------------------------------------------------------------
    # Default SEO / OG fallbacks
    # ------------------------------------------------------------------
    meta_title = models.CharField(
        max_length=160,
        default="MAGIC MASALA — Authentic Indian Spices, Delivered",
        help_text="Used on pages that haven't set their own title.",
    )
    meta_description = models.TextField(
        max_length=320,
        blank=True,
        default="MAGIC MASALA — Premium authentic Indian masalas and spices stone-ground fresh. Richer aroma and unforgettable flavour in every meal.",
        help_text="Site-wide default meta description (used on pages without one).",
    )
    og_image = models.ImageField(
        upload_to="seo/",
        null=True,
        blank=True,
        help_text="Default Open Graph image for social sharing. 1200×630 px, JPG/WebP, under 200KB.",
    )
    fssai_license_number = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = "Site Settings"

    def __str__(self):
        return "Site Settings"

    # ------------------------------------------------------------------
    # Computed helpers (used by checkout logic)
    # ------------------------------------------------------------------
    def compute_cod_advance(self, order_total: Decimal) -> Decimal:
        """Return the advance amount due online when COD is selected."""
        if self.cod_advance_mode == "fixed":
            return min(self.cod_advance_amount, order_total).quantize(Decimal("0.01"))
        return (order_total * self.cod_advance_percent / Decimal("100")).quantize(Decimal("0.01"))

    def compute_cod_remaining(self, order_total: Decimal) -> Decimal:
        """Return the amount collected at the doorstep (including any COD charge)."""
        advance = self.compute_cod_advance(order_total)
        return max(Decimal("0.00"), order_total - advance + self.cod_charge)


class EmailSettings(SingletonModel):
    """
    Master control panel for email notifications, Brevo SMTP settings, and templates.
    Editable in Admin → Marketing & Emails → Email Settings & Brevo.
    """
    is_enabled = models.BooleanField(
        default=True,
        help_text="Master toggle to enable or disable all outgoing emails.",
    )

    # Brevo SMTP Configuration Overrides (defaults to settings/env if left blank)
    smtp_host = models.CharField(
        max_length=120,
        default="smtp-relay.brevo.com",
        help_text="SMTP Relay Host (e.g. smtp-relay.brevo.com)",
    )
    smtp_port = models.PositiveIntegerField(
        default=587,
        help_text="SMTP Port (587 for TLS, 465 for SSL)",
    )
    smtp_use_tls = models.BooleanField(
        default=True,
        help_text="Use TLS for secure email transport.",
    )
    smtp_user = models.CharField(
        max_length=150,
        default="care@mumagicmasala.com",
        help_text="Brevo SMTP login / account email.",
    )
    smtp_password = models.CharField(
        max_length=255,
        default="",
        blank=True,
        help_text="Brevo SMTP Key (xsmtpsib-...) — set this in admin, never hardcode.",
    )
    from_name = models.CharField(
        max_length=100,
        default="MU Magic Masala",
        help_text="Sender display name seen in inbox.",
    )
    from_email = models.EmailField(
        default="care@mumagicmasala.com",
        help_text="Sender email address.",
    )
    support_email = models.EmailField(
        default="care@mumagicmasala.com",
        help_text="Reply-to email for customer queries.",
    )
    support_phone = models.CharField(
        max_length=25,
        default="7805105024",
        blank=True,
        help_text="Support telephone / WhatsApp shown in email footers.",
    )

    # Feature Toggles & Subject Lines
    welcome_email_enabled = models.BooleanField(
        default=True,
        help_text="Send a branded welcome email with coupon when a new customer registers.",
    )
    welcome_email_subject = models.CharField(
        max_length=255,
        default="Welcome to MU Magic Masala! 🌶️ Enjoy 10% Off Your First Order",
    )
    welcome_coupon_code = models.CharField(
        max_length=50,
        default="WELCOME10",
        blank=True,
        help_text="Special discount coupon code to highlight in welcome email.",
    )

    order_confirmation_enabled = models.BooleanField(
        default=True,
        help_text="Send itemized order confirmation email immediately after payment/checkout.",
    )
    order_confirmation_subject = models.CharField(
        max_length=255,
        default="Order Confirmed — #{order_number} | MU Magic Masala",
    )

    order_status_update_enabled = models.BooleanField(
        default=True,
        help_text="Send tracking & delivery status update email when order status changes in admin.",
    )
    order_status_subject = models.CharField(
        max_length=255,
        default="Order Update: #{order_number} is now {status_display} | MU Magic Masala",
    )

    password_change_enabled = models.BooleanField(
        default=True,
        help_text="Send security confirmation email when customer updates their password.",
    )
    password_change_subject = models.CharField(
        max_length=255,
        default="Security Alert: Your MU Magic Masala Password Was Changed",
    )

    abandoned_cart_enabled = models.BooleanField(
        default=True,
        help_text="Send friendly reminders to customers who left items in their cart.",
    )
    abandoned_cart_subject = models.CharField(
        max_length=255,
        default="You left something delicious behind! 🌶️ Complete your order at MU Magic Masala",
    )

    footer_text = models.TextField(
        default="Pure, cold stone-ground, preservative-free Indian spices straight from our mill to your kitchen.",
        blank=True,
        help_text="Custom brand message shown at the bottom of all emails.",
    )

    class Meta:
        verbose_name = "Email Settings & Brevo"
        verbose_name_plural = "Email Settings & Brevo"

    def __str__(self):
        return "Email Settings & Brevo Configuration"


class EmailCampaign(models.Model):
    """
    Marketing campaigns, festival offers, and discount blasts.
    Admin can compose, preview, send test email, and broadcast to all registered customers.
    """
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENDING = "sending", "Sending in progress"
        SENT = "sent", "Sent Successfully"
        FAILED = "failed", "Failed"

    title = models.CharField(
        max_length=200,
        help_text="Internal campaign name (e.g. 'Diwali 20% Off Mega Combo Blast')",
    )
    subject = models.CharField(
        max_length=255,
        help_text="Subject line that customers will see in their email inbox.",
    )
    preview_text = models.CharField(
        max_length=255,
        blank=True,
        help_text="Teaser line shown in inbox snippet (e.g. 'Handcrafted spices at unbeatable festive prices.')",
    )
    badge_text = models.CharField(
        max_length=60,
        default="SPECIAL FESTIVE OFFER",
        blank=True,
        help_text="Highlight badge e.g. 'LIMITED TIME OFFER', 'NEW ARRIVAL', 'FESTIVAL SPECIAL'",
    )
    heading = models.CharField(
        max_length=200,
        default="Bring Richer Aroma to Every Meal",
        help_text="Main headline inside the email.",
    )
    subheading = models.CharField(
        max_length=300,
        blank=True,
        default="Authentic stone-ground spices made with traditional recipes and zero preservatives.",
    )
    banner_image_url = models.URLField(
        blank=True,
        help_text="Optional header banner image URL (e.g. https://.../banner.jpg)",
    )
    message_body = models.TextField(
        help_text="Offer announcement message body. HTML paragraphs or plain text allowed.",
        default="We are excited to bring you an exclusive discount on our best-selling fresh-ground Indian spices and custom combo boxes. Treat your family to unforgettable taste!",
    )
    coupon_code = models.CharField(
        max_length=50,
        blank=True,
        help_text="Discount coupon code to display in prominent voucher badge (e.g. FESTIVE20).",
    )
    discount_highlight = models.CharField(
        max_length=60,
        blank=True,
        default="FLAT 20% OFF",
        help_text="e.g. 'FLAT 20% OFF', 'BUY 1 GET 1 FREE', 'EXTRA ₹100 OFF'",
    )
    cta_text = models.CharField(
        max_length=60,
        default="Explore Spice Combos Now",
        help_text="Button text inside the email.",
    )
    cta_url = models.CharField(
        max_length=255,
        default="/combos/",
        help_text="URL where the button takes customers (relative e.g. /combos/ or absolute).",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    recipients_sent = models.PositiveIntegerField(
        default=0,
        help_text="Total number of customers who received this campaign.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Email Campaign & Offer"
        verbose_name_plural = "Email Campaigns & Offers"

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


class EmailLog(models.Model):
    """
    Tracks and audits every outgoing email with timestamp, recipient, status, and error details.
    """
    class EmailType(models.TextChoices):
        WELCOME = "welcome", "Welcome Registration"
        ORDER_CONFIRMATION = "order_confirmation", "Order Confirmation"
        STATUS_UPDATE = "status_update", "Order Status Update"
        PASSWORD_RESET = "password_reset", "Password Reset Link"
        PASSWORD_CHANGE = "password_change", "Password Change Alert"
        CAMPAIGN = "campaign", "Offer / Marketing Campaign"
        TEST = "test", "Brevo Connection Test"
        OTHER = "other", "Other Notification"

    class Status(models.TextChoices):
        SENT = "sent", "Sent Successfully"
        FAILED = "failed", "Delivery Failed"

    email_type = models.CharField(max_length=30, choices=EmailType.choices, default=EmailType.OTHER)
    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.SENT)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Email Delivery Log"
        verbose_name_plural = "Email Delivery Logs"

    def __str__(self):
        return f"[{self.get_status_display()}] {self.recipient} — {self.subject} ({self.created_at.strftime('%d %b %H:%M')})"


