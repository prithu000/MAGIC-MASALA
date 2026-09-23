"""
apps/orders/tasks.py — Celery tasks for order notifications.
"""

import logging

from celery import shared_task
from django.conf import settings
from apps.core.email_service import (
    send_order_confirmation_email as deliver_order_confirmation,
    send_order_status_update_email as deliver_order_status_update,
    send_templated_email,
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_confirmation_email(self, order_id: int):
    from .models import Order

    try:
        order = Order.objects.select_related("user").prefetch_related("items").get(pk=order_id)
        deliver_order_confirmation(order)
        logger.info("Order confirmation dispatched for order %s", order.order_number)
    except Exception as exc:
        logger.error("Failed to dispatch order confirmation for order_id=%s: %s", order_id, exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_status_update_email(self, order_id: int, status: str):
    from .models import Order

    try:
        order = Order.objects.select_related("user").get(pk=order_id)
        deliver_order_status_update(order, status_display=status, status_code=order.order_status)
        logger.info("Order status update dispatched for order %s", order.order_number)
    except Exception as exc:
        logger.error("Failed to dispatch status update for order_id=%s: %s", order_id, exc)
        raise self.retry(exc=exc)


@shared_task
def send_abandoned_cart_reminders():
    """
    Find carts not updated in 24h that belong to users with email,
    and send a branded reminder email with cart items.
    """
    from datetime import timedelta
    from django.utils import timezone
    from apps.cart.models import Cart
    from apps.core.email_service import get_email_settings

    email_settings = get_email_settings()
    if email_settings and not email_settings.abandoned_cart_enabled:
        return

    cutoff = timezone.now() - timedelta(hours=24)
    carts = (
        Cart.objects.filter(
            user__isnull=False,
            updated_at__lt=cutoff,
            updated_at__gt=cutoff - timedelta(hours=1),
        )
        .exclude(items__isnull=True)
        .select_related("user")
        .prefetch_related("items__product")
    )

    for cart in carts:
        if cart.user.email and cart.items.exists():
            try:
                subject = email_settings.abandoned_cart_subject if email_settings else "You left something delicious behind! 🌶️ MU Magic Masala"
                send_templated_email(
                    subject=subject,
                    template_name="emails/abandoned_cart.html",
                    context={
                        "user": cart.user,
                        "items": cart.items.all(),
                        "preview_text": "Your hand-selected authentic spices are waiting in your cart.",
                    },
                    recipient_list=[cart.user.email],
                    email_type="other",
                    async_send=True,
                )
            except Exception as e:
                logger.error("Failed to send abandoned cart reminder to %s: %s", cart.user.email, e)

