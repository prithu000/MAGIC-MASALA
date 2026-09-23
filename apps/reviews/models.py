"""
apps/reviews/models.py
ProductReview — owner approves before it goes live.
"""

from django.contrib.auth import get_user_model
from django.db import models

from apps.core.validators import validate_image_size, validate_image_type

User = get_user_model()


class ProductReview(models.Model):
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(help_text="Rating from 1 to 5.")
    title = models.CharField(max_length=150, blank=True)
    comment = models.TextField()
    image = models.ImageField(
        upload_to="reviews/",
        null=True,
        blank=True,
        validators=[validate_image_size, validate_image_type],
        help_text="Optional photo with the review.",
    )
    is_approved = models.BooleanField(
        default=False,
        help_text="Check this box to make the review visible on the product page.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("product", "user")]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.email} — {self.product.name} ({self.rating}★)"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._update_product_rating()

    def delete(self, *args, **kwargs):
        product = self.product
        super().delete(*args, **kwargs)
        self._update_product_rating(product=product)

    def _update_product_rating(self, product=None):
        """Recompute and store the denormalized average_rating on the Product."""
        from django.db.models import Avg, Count
        from decimal import Decimal

        target = product or self.product
        result = ProductReview.objects.filter(product=target, is_approved=True).aggregate(
            avg=Avg("rating"), count=Count("id")
        )
        target.average_rating = result["avg"] or Decimal("0.00")
        target.review_count = result["count"] or 0
        target.save(update_fields=["average_rating", "review_count"])
