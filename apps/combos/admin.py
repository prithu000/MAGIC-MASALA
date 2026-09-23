"""apps/combos/admin.py"""

from django.contrib import admin
from imagekit.admin import AdminThumbnail
from unfold.admin import ModelAdmin, TabularInline

from .models import CustomizeComboEligibleProduct, CustomizeComboRule, FixedCombo, FixedComboItem


class FixedComboItemInline(TabularInline):
    model = FixedComboItem
    extra = 1
    fields = ("product", "quantity")
    autocomplete_fields = ["product"]


class CustomizeComboEligibleProductInline(TabularInline):
    model = CustomizeComboEligibleProduct
    extra = 0
    autocomplete_fields = ["product"]
    readonly_fields = ("product_category", "product_price")
    fields = ("product", "product_category", "product_price")

    @admin.display(description="Category")
    def product_category(self, obj):
        return obj.product.category.name if obj.product and obj.product.category else "—"

    @admin.display(description="Price")
    def product_price(self, obj):
        return f"₹{obj.product.price:.0f}" if obj.product else "—"


@admin.register(CustomizeComboEligibleProduct)
class CustomizeComboEligibleProductAdmin(ModelAdmin):
    list_display = ("product", "product_category", "product_price", "rule")
    list_filter = ("rule", "product__category")
    search_fields = ("product__name", "product__sku")
    autocomplete_fields = ["product"]

    @admin.display(description="Category")
    def product_category(self, obj):
        return obj.product.category.name if obj.product and obj.product.category else "—"

    @admin.display(description="Price")
    def product_price(self, obj):
        return f"₹{obj.product.price:.0f}" if obj.product else "—"


@admin.register(FixedCombo)
class FixedComboAdmin(ModelAdmin):
    list_display = ("name", "combo_price", "is_featured_on_homepage", "is_active", "display_order", "admin_thumbnail")
    list_editable = ("is_featured_on_homepage", "is_active", "display_order")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("admin_thumbnail", "total_mrp_display", "savings_display")
    inlines = [FixedComboItemInline]

    admin_thumbnail = AdminThumbnail(image_field="image")

    fieldsets = (
        (None, {"fields": ("name", "slug", "image", "admin_thumbnail", "description", "combo_price", "is_featured_on_homepage", "is_active", "display_order")}),
        ("Savings (calculated)", {"fields": ("total_mrp_display", "savings_display"), "classes": ("collapse",)}),
        ("SEO", {"fields": ("meta_title", "meta_description"), "classes": ("collapse",)}),
    )

    @admin.display(description="Total MRP of items")
    def total_mrp_display(self, obj):
        return f"₹{obj.total_mrp:.2f}" if obj.pk else "—"

    @admin.display(description="Customer savings")
    def savings_display(self, obj):
        return f"₹{obj.savings:.2f}" if obj.pk else "—"


@admin.register(CustomizeComboRule)
class CustomizeComboRuleAdmin(ModelAdmin):
    list_display = (
        "name",
        "required_item_count",
        "max_units_per_product",
        "fixed_price",
        "eligible_mode",
        "eligible_count_display",
        "is_active",
    )
    list_editable = ("required_item_count", "max_units_per_product", "fixed_price", "is_active")
    search_fields = ("name", "display_title", "description")
    readonly_fields = ("eligible_count_display",)
    inlines = [CustomizeComboEligibleProductInline]
    actions = ["sync_all_active_spices_to_combo"]

    fieldsets = (
        (
            "Build Your Own Combo Configuration",
            {
                "fields": (
                    "name",
                    "slug",
                    "display_title",
                    "description",
                    "rule_type",
                    "required_item_count",
                    "max_units_per_product",
                    "fixed_price",
                    "free_product",
                    "is_active",
                ),
                "description": (
                    "Configure combo box size (e.g. 10 products), max quantity per individual product (e.g. max 2 of any single spice), "
                    "and the flat price (e.g. ₹999.00). Changes apply immediately on the website."
                ),
            },
        ),
        (
            "Product Eligibility Filter",
            {
                "fields": ("eligible_mode", "price_cap", "eligible_count_display"),
                "description": (
                    "Auto mode automatically includes all active catalog spices at or under the price cap and syncs them below. "
                    "Manual mode lets you hand-pick exact products using the table below."
                ),
            },
        ),
    )
    help_text_overrides = {
        "required_item_count": "Total items customer must select to complete the combo (e.g. 10).",
        "max_units_per_product": "Maximum units of any individual product customer can add (e.g. max 2 per spice).",
        "fixed_price": "Flat price charged for the completed combo box (e.g. ₹999.00).",
        "eligible_mode": (
            "Auto: automatically includes all active products at or under the price cap and keeps the table below in sync. "
            "Manual: only the products listed in the table below."
        ),
    }

    @admin.display(description="Active Spices on Web")
    def eligible_count_display(self, obj):
        if not obj or not obj.pk:
            return "—"
        count = obj.get_eligible_products().count()
        mode_label = "Auto (all active spices)" if obj.eligible_mode == CustomizeComboRule.EligibleMode.AUTO else "Manual (hand-picked list below)"
        return f"✅ {count} products live on website ({mode_label})"

    @admin.action(description="Sync all active catalog spices to this combo")
    def sync_all_active_spices_to_combo(self, request, queryset):
        from apps.catalog.models import Product
        active_products = Product.objects.filter(is_active=True, is_customize_combo_eligible=True)
        total_synced = 0
        for rule in queryset:
            for p in active_products:
                _, created = CustomizeComboEligibleProduct.objects.get_or_create(rule=rule, product=p)
                if created:
                    total_synced += 1
        self.message_user(request, f"Successfully synced all active products. {total_synced} new products linked.")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # If in auto mode, automatically ensure all eligible active products exist in CustomizeComboEligibleProduct
        if obj.eligible_mode == CustomizeComboRule.EligibleMode.AUTO:
            try:
                from apps.catalog.models import Product
                qs = Product.objects.filter(is_active=True, is_customize_combo_eligible=True)
                if obj.price_cap:
                    qs = qs.filter(price__lte=obj.price_cap)
                current_pids = set(obj.eligible_products.values_list("product_id", flat=True))
                target_pids = set(qs.values_list("id", flat=True))
                to_create = [
                    CustomizeComboEligibleProduct(rule=obj, product_id=pid)
                    for pid in (target_pids - current_pids)
                ]
                if to_create:
                    CustomizeComboEligibleProduct.objects.bulk_create(to_create, ignore_conflicts=True)
            except Exception:
                pass

        # Keep SiteSettings in sync with the primary active rule
        if obj.is_active:
            try:
                from apps.core.models import SiteSettings
                settings = SiteSettings.get_solo()
                settings.customize_combo_item_count = obj.required_item_count
                settings.customize_combo_max_units_per_product = obj.max_units_per_product
                if obj.fixed_price:
                    settings.customize_combo_price = obj.fixed_price
                settings.save(update_fields=[
                    "customize_combo_item_count",
                    "customize_combo_max_units_per_product",
                    "customize_combo_price",
                ])
            except Exception:
                pass
