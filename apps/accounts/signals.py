"""
apps/accounts/signals.py
Auto-create CustomerProfile when a new User is created.
"""

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CustomerProfile

User = get_user_model()


@receiver(post_save, sender=User)
def create_customer_profile(sender, instance, created, **kwargs):
    if created:
        CustomerProfile.objects.get_or_create(user=instance)
        # Dispatch welcome email with coupon code
        try:
            from apps.core.email_service import send_welcome_email
            send_welcome_email(instance)
        except Exception:
            pass
