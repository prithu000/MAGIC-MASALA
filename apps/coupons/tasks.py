"""apps/coupons/tasks.py — Periodic task to deactivate expired coupons."""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def deactivate_expired_coupons():
    """
    Runs hourly via Celery Beat.
    Sets is_active=False on coupons past their valid_to datetime.
    Coupons are also checked at order time, so this is belt-and-suspenders.
    """
    from .models import Coupon

    expired = Coupon.objects.filter(is_active=True, valid_to__lt=timezone.now())
    count = expired.update(is_active=False)
    if count:
        logger.info("Deactivated %d expired coupons", count)
