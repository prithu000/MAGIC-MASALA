"""
apps/accounts/models.py
CustomerProfile, Address, Wishlist
"""

from django.contrib.auth import get_user_model
from django.db import models
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFill

from apps.core.validators import validate_image_size, validate_image_type

User = get_user_model()


class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=15, blank=True)
    alternate_phone = models.CharField(max_length=15, blank=True)
    avatar = ProcessedImageField(
        upload_to="avatars/",
        processors=[ResizeToFill(300, 300)],
        format="JPEG",
        options={"quality": 80},
        validators=[validate_image_size, validate_image_type],
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"Profile — {self.user.get_full_name() or self.user.username}"


class Address(models.Model):
    class AddressType(models.TextChoices):
        HOME = "home", "Home"
        WORK = "work", "Work"
        OTHER = "other", "Other"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=15)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    landmark = models.CharField(max_length=150, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    address_type = models.CharField(max_length=10, choices=AddressType.choices, default=AddressType.HOME)
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Addresses"
        ordering = ["-is_default", "-id"]

    def __str__(self):
        return f"{self.full_name}, {self.city} — {self.pincode}"

    def save(self, *args, **kwargs):
        # Ensure only one default address per user
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wishlist")
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="wishlisted_by")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "product")]
        ordering = ["-added_at"]

    def __str__(self):
        return f"{self.user.username} — {self.product.name}"
