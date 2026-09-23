"""
apps/combos/models.py
FixedCombo, FixedComboItem, CustomizeComboRule, CustomizeComboEligibleProduct, CustomComboSelection
"""

from django.contrib.auth import get_user_model
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFill

from apps.core.validators import validate_image_size, validate_image_type

User = get_user_model()


class FixedCombo(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    image = ProcessedImageField(
        upload_to="combos/",
        processors=[ResizeToFill(1200, 1200)],
        format="JPEG",
        options={"quality": 85},
        null=True,
        blank=True,
        validators=[validate_image_size, validate_image_type],
        help_text="Recommended: 1200×1200 px, JPG/WebP. Auto-resized on upload.",
    )
    description = models.TextField(blank=True)
    combo_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    is_featured_on_homepage = models.BooleanField(
        default=False,
        help_text="Show this combo in the Featured Spotlight on the homepage. (Only 1 combo will be featured on the homepage; all others appear under 'More Combos')."
    )
    display_order = models.PositiveSmallIntegerField(default=0)
    meta_title = models.CharField(max_length=160, blank=True)
    meta_description = models.TextField(max_length=320, blank=True)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("combos:fixed_combo_detail", kwargs={"slug": self.slug})

    @property
    def total_mrp(self):
        """Sum of MRPs (or prices) of included items — for showing savings."""
        total = sum(
            (item.product.mrp or item.product.price) * item.quantity
            for item in self.items.select_related("product").all()
        )
        return total

    @property
    def total_individual_price(self):
        """Sum of regular individual selling prices of included items."""
        return sum(
            item.product.price * item.quantity
            for item in self.items.select_related("product").all()
        )

    @property
    def savings(self):
        return max(0, self.total_mrp - self.combo_price)

    @property
    def savings_percentage(self):
        if self.total_mrp and self.total_mrp > self.combo_price:
            return int(((self.total_mrp - self.combo_price) / self.total_mrp) * 100)
        return 0


class FixedComboItem(models.Model):
    combo = models.ForeignKey(FixedCombo, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT, related_name="combo_items")
    quantity = models.PositiveSmallIntegerField(default=1)

    class Meta:
        unique_together = [("combo", "product")]

    def __str__(self):
        return f"{self.quantity}× {self.product.name} in {self.combo.name}"


class CustomizeComboRule(models.Model):
    class EligibleMode(models.TextChoices):
        AUTO = "auto", "Auto (all products at or under price cap)"
        MANUAL = "manual", "Manual (hand-picked list below)"

    class RuleType(models.TextChoices):
        FIXED_PRICE = "fixed_price", "Fixed Price (e.g. 10 for ₹999)"
        BUY_N_GET_FREE = "buy_n_get_free", "Buy N Get 1 Free (e.g. 5 Masalas + Free All-In-One)"

    name = models.CharField(max_length=100, default="Build Your Own Combo")
    slug = models.SlugField(max_length=120, unique=True, blank=True, null=True)
    rule_type = models.CharField(
        max_length=20,
        choices=RuleType.choices,
        default=RuleType.FIXED_PRICE,
    )
    display_title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    required_item_count = models.PositiveSmallIntegerField(
        default=10,
        help_text="Number of products the customer must select to complete the combo.",
    )
    max_units_per_product = models.PositiveSmallIntegerField(
        default=2,
        help_text="Maximum quantity of any single product allowed in this combo box (e.g. max 2 of the same masala).",
    )
    fixed_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=999,
        help_text="Fixed price charged for a completed combo (used when rule_type is Fixed Price).",
    )
    free_product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Bonus product given completely FREE when the customer selects the required items.",
    )
    eligible_mode = models.CharField(
        max_length=10,
        choices=EligibleMode.choices,
        default=EligibleMode.AUTO,
    )
    price_cap = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="(Auto mode only) Include all products priced at or below this amount.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Build-Your-Own Combo Rule"

    def __str__(self):
        return f"{self.name} ({self.get_rule_type_display()})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_eligible_products(self):
        """Return the queryset of products a customer can choose from."""
        from apps.catalog.models import Product

        base = Product.objects.filter(is_active=True, is_customize_combo_eligible=True)
        if self.eligible_mode == self.EligibleMode.AUTO:
            if self.price_cap:
                return base.filter(price__lte=self.price_cap)
            return base
        else:
            manual_ids = self.eligible_products.values_list("product_id", flat=True)
            return base.filter(pk__in=manual_ids)


class CustomizeComboEligibleProduct(models.Model):
    rule = models.ForeignKey(CustomizeComboRule, on_delete=models.CASCADE, related_name="eligible_products")
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE)

    class Meta:
        unique_together = [("rule", "product")]

    def __str__(self):
        return f"{self.product.name} — eligible for {self.rule.name}"


class CustomComboSelection(models.Model):
    """Tracks a customer's product selections for a Build-Your-Own combo."""

    rule = models.ForeignKey(CustomizeComboRule, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, blank=True)
    selected_products = models.ManyToManyField("catalog.Product", blank=True)
    items_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Mapping of product_id to selected quantity, e.g. {'13': 2, '12': 1}.",
    )
    free_product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    combo_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    savings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_complete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        total_units = (
            sum(int(q) for q in self.items_json.values())
            if self.items_json
            else self.selected_products.count()
        )
        free_note = f" + FREE {self.free_product.name}" if self.free_product else ""
        return f"{self.rule.name} ({total_units}/{self.rule.required_item_count} items{free_note}) — ₹{self.combo_price}"

    @property
    def item_count(self):
        if self.items_json:
            return sum(int(q) for q in self.items_json.values())
        return self.selected_products.count()

    def get_items(self):
        """Return list of dicts: [{'product': product, 'quantity': qty}]"""
        if self.items_json:
            from apps.catalog.models import Product
            p_ids = [int(pid) for pid in self.items_json.keys() if str(pid).isdigit()]
            products = {p.id: p for p in Product.objects.filter(id__in=p_ids)}
            result = []
            for pid_str, qty in self.items_json.items():
                try:
                    pid = int(pid_str)
                    if pid in products:
                        result.append({"product": products[pid], "quantity": int(qty)})
                except (ValueError, TypeError):
                    continue
            return result
        return [{"product": p, "quantity": 1} for p in self.selected_products.all()]

