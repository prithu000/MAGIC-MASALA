"""
apps/catalog/admin.py
Premium product admin with inline images, variants, thumbnail preview.
"""

from django.contrib import admin
from django.utils.html import format_html
from imagekit.admin import AdminThumbnail
from unfold.admin import ModelAdmin, StackedInline, TabularInline

from .models import Category, Product, ProductImage, ProductVariant, Tag


class ProductImageInline(TabularInline):
    model = ProductImage
    extra = 1
    max_num = 6
    fields = ("image", "alt_text", "display_order", "admin_thumbnail")
    readonly_fields = ("admin_thumbnail",)

    admin_thumbnail = AdminThumbnail(image_field="thumbnail")


class ProductVariantInline(TabularInline):
    model = ProductVariant
    extra = 1
    fields = ("size_label", "sku", "price", "mrp", "stock_quantity", "is_active", "display_order")


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = (
        "admin_thumbnail",
        "name",
        "category",
        "price",
        "stock_quantity",
        "is_active",
        "is_customize_combo_eligible",
        "is_featured",
        "is_bestseller",
        "average_rating",
    )
    list_display_links = ("name",)
    list_filter = ("category", "is_active", "is_customize_combo_eligible", "is_featured", "is_bestseller", "tags")
    list_editable = ("is_active", "is_customize_combo_eligible", "is_featured", "is_bestseller")
    search_fields = ("name", "sku", "slug")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("admin_thumbnail", "average_rating", "review_count", "created_at", "updated_at")
    filter_horizontal = ("tags",)
    inlines = [ProductVariantInline, ProductImageInline]
    save_on_top = True
    actions = ["make_combo_eligible", "remove_combo_eligible"]

    @admin.action(description="Enable selected products for Build-Your-Own Combo")
    def make_combo_eligible(self, request, queryset):
        count = queryset.update(is_customize_combo_eligible=True)
        from apps.combos.models import CustomizeComboRule, CustomizeComboEligibleProduct
        rule = CustomizeComboRule.objects.filter(is_active=True).first()
        if rule:
            for p in queryset:
                CustomizeComboEligibleProduct.objects.get_or_create(rule=rule, product=p)
        self.message_user(request, f"{count} products enabled for custom combos.")

    @admin.action(description="Remove selected products from Build-Your-Own Combo")
    def remove_combo_eligible(self, request, queryset):
        count = queryset.update(is_customize_combo_eligible=False)
        from apps.combos.models import CustomizeComboEligibleProduct
        CustomizeComboEligibleProduct.objects.filter(product__in=queryset).delete()
        self.message_user(request, f"{count} products removed from custom combos.")

    admin_thumbnail = AdminThumbnail(image_field="thumbnail")
    admin_thumbnail.short_description = "Image"

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("name", "slug", "sku", "category", "tags")},
        ),
        (
            "Description",
            {"fields": ("short_description", "description")},
        ),
        (
            "Product Tabs & Accordions (Zoff Style)",
            {
                "fields": ("ingredients", "how_to_use", "storage_instructions", "features"),
                "description": "These fields control the collapsible accordion tabs (Ingredients, How to Use, Freshness Storage, and Quality Tags) on the product page.",
            },
        ),
        (
            "Pricing & Stock",
            {"fields": ("price", "mrp", "stock_quantity")},
        ),
        (
            "Main Image",
            {"fields": ("main_image", "admin_thumbnail", "main_image_alt")},
        ),
        (
            "Visibility",
            {
                "fields": (
                    "is_active",
                    "is_featured",
                    "is_bestseller",
                    "is_customize_combo_eligible",
                )
            },
        ),
        (
            "SEO",
            {
                "fields": ("meta_title", "meta_description"),
                "classes": ("collapse",),
            },
        ),
        (
            "Statistics (read-only)",
            {
                "fields": ("average_rating", "review_count", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("name", "is_active", "display_order", "admin_thumbnail")
    list_editable = ("is_active", "display_order")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("admin_thumbnail",)

    admin_thumbnail = AdminThumbnail(image_field="image")
    admin_thumbnail.short_description = "Image"


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
