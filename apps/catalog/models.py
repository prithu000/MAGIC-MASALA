"""
apps/catalog/models.py
Category, Tag, Product, ProductVariant, ProductImage
"""

from decimal import Decimal

from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from imagekit.models import ImageSpecField, ProcessedImageField
from imagekit.processors import ResizeToFill, ResizeToFit
from ckeditor.fields import RichTextField

from apps.core.validators import validate_image_size, validate_image_type


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=110, unique=True)
    image = ProcessedImageField(
        upload_to="categories/",
        processors=[ResizeToFill(600, 600)],
        format="JPEG",
        options={"quality": 85},
        null=True,
        blank=True,
        validators=[validate_image_size, validate_image_type],
        help_text="Recommended: 600×600 px, JPG/WebP. File is auto-resized on upload.",
    )
    description = RichTextField(blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    meta_title = models.CharField(max_length=160, blank=True)
    meta_description = models.TextField(max_length=320, blank=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:category_detail", kwargs={"slug": self.slug})


class Tag(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    sku = models.CharField(max_length=60, unique=True, blank=True, help_text="Unique product code (e.g. MU-GM-100G). Auto-generated if left blank.")
    description = RichTextField(blank=True, help_text="Full product description — use the rich-text editor.")
    short_description = models.TextField(
        max_length=300,
        blank=True,
        help_text="Brief description shown on listing cards (max 300 characters).",
    )
    ingredients = models.TextField(
        blank=True,
        help_text="List of ingredients, e.g. Coriander Seeds, Cumin, Black Pepper, Green Cardamom, Cinnamon, Cloves, Bay Leaf, Ginger.",
    )
    how_to_use = models.TextField(
        blank=True,
        help_text="Usage and recipe instructions, e.g. Add 1 tsp near the end of cooking or in tadka to lock aroma.",
    )
    storage_instructions = models.CharField(
        max_length=255,
        blank=True,
        default="Store in a cool, dry place away from direct sunlight. Reseal airtight zip-lock after every use.",
        help_text="Storage and freshness advice shown in the product accordion.",
    )
    features = models.CharField(
        max_length=255,
        blank=True,
        default="100% Pure, Cold Stone Ground, Zero Preservatives, No Artificial Colors",
        help_text="Key quality highlights, comma separated.",
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="products")

    # Pricing & Tax
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Selling price in ₹ (inclusive of GST).")
    mrp = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum retail price (MRP) shown as a strike-through. Leave blank if no discount.",
    )
    hsn_code = models.CharField(
        max_length=8,
        default="0910",
        blank=True,
        help_text="4-digit HSN/SAC code for GST (e.g. 0910 for Spices/Turmeric, 0904 for Chilli, 0909 for Coriander/Cumin, 2001 for Pickles, 2501 for Salts).",
    )
    gst_rate = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("5.00"),
        help_text="Applicable GST rate in percentage (e.g. 5.00 for 5%).",
    )

    # Inventory
    stock_quantity = models.PositiveIntegerField(default=0)

    # Main image — auto-resized to 1200×1200 on upload
    main_image = ProcessedImageField(
        upload_to="products/",
        processors=[ResizeToFill(1200, 1200)],
        format="JPEG",
        options={"quality": 85},
        null=True,
        blank=True,
        validators=[validate_image_size, validate_image_type],
        help_text="Recommended: 1200×1200 px, square, neutral background. File is auto-resized on upload.",
    )
    main_image_alt = models.CharField(
        max_length=200,
        blank=True,
        help_text="Alt text for the main image (important for SEO and accessibility).",
    )

    # Thumbnail derived from main_image — used in listing cards
    thumbnail = ImageSpecField(
        source="main_image",
        processors=[ResizeToFill(400, 400)],
        format="JPEG",
        options={"quality": 80},
    )

    # Flags
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False, help_text="Show in the Featured section on the homepage.")
    is_bestseller = models.BooleanField(default=False, help_text="Show in the Bestsellers row on the homepage.")
    is_customize_combo_eligible = models.BooleanField(
        default=True,
        help_text="Can this product be selected when building a custom combo?",
    )

    # Denormalized ratings (updated by signal when a review is approved)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0.00"))
    review_count = models.PositiveIntegerField(default=0)

    # SEO
    meta_title = models.CharField(max_length=160, blank=True)
    meta_description = models.TextField(max_length=320, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.sku:
            import uuid
            self.sku = f"MU-{slugify(self.name)[:20].upper()}-{uuid.uuid4().hex[:4].upper()}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(
            "catalog:product_detail",
            kwargs={"category_slug": self.category.slug, "slug": self.slug},
        )

    @property
    def effective_price(self):
        """Return the current selling price of the product."""
        return self.price

    @property
    def discount_percent(self) -> int | None:
        """Return integer discount percentage if MRP is set and higher than price."""
        if self.mrp and self.mrp > self.price:
            return int(((self.mrp - self.price) / self.mrp) * 100)
        return None

    @property
    def savings_amount(self):
        if self.mrp and self.mrp > self.price:
            return self.mrp - self.price
        return Decimal("0.00")

    @property
    def is_in_stock(self) -> bool:
        return self.stock_quantity > 0

    @property
    def is_low_stock(self) -> bool:
        """True when stock is between 1 and 10 — triggers scarcity indicator."""
        return 1 <= self.stock_quantity <= 10

    @property
    def default_size_label(self) -> str:
        """Return actual pack quantity and packaging, e.g. '200 gm Box', '125 gm Box', '100 gm Box'."""
        first_variant = self.variants.filter(is_active=True).first() or self.variants.first()
        if first_variant and first_variant.size_label:
            val = first_variant.size_label.strip()
            if "box" in val.lower():
                return val
            return f"{val} Box"
        return "Box"


class ProductVariant(models.Model):
    """Pack sizes — e.g. 50g, 100g, 250g, 500g, 1kg."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    size_label = models.CharField(max_length=30, help_text='e.g. "50g", "100g", "500g", "1kg"')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    mrp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    sku = models.CharField(max_length=60, unique=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "size_label"]
        unique_together = [("product", "size_label")]

    def __str__(self):
        return f"{self.product.name} — {self.size_label}"

    @property
    def is_in_stock(self) -> bool:
        return self.stock_quantity > 0

    @property
    def discount_percent(self) -> int | None:
        if self.mrp and self.mrp > self.price:
            return int(((self.mrp - self.price) / self.mrp) * 100)
        return None

    @property
    def savings_amount(self):
        if self.mrp and self.mrp > self.price:
            return self.mrp - self.price
        return Decimal("0.00")


class ProductImage(models.Model):
    """Additional gallery images for the product detail page (up to 6)."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="gallery_images")
    image = ProcessedImageField(
        upload_to="products/gallery/",
        processors=[ResizeToFill(1200, 1200)],
        format="JPEG",
        options={"quality": 85},
        validators=[validate_image_size, validate_image_type],
        help_text="Recommended: 1200×1200 px. Up to 6 gallery images per product. Auto-resized on upload.",
    )
    alt_text = models.CharField(
        max_length=200,
        blank=True,
        help_text="Describe what is shown in this image (important for SEO and screen readers).",
    )
    display_order = models.PositiveSmallIntegerField(default=0)

    thumbnail = ImageSpecField(
        source="image",
        processors=[ResizeToFill(150, 150)],
        format="JPEG",
        options={"quality": 80},
    )

    class Meta:
        ordering = ["display_order"]

    def __str__(self):
        return f"Image {self.display_order} — {self.product.name}"
