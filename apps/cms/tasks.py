"""apps/cms/tasks.py — Celery Beat tasks for scheduled CMS content."""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def activate_scheduled_hero_slides():
    """
    Runs every 15 minutes.
    Activates slides whose start_datetime has passed and deactivates those past end_datetime.
    """
    from .models import HeroSlide

    now = timezone.now()

    # Activate slides that should now be running
    to_activate = HeroSlide.objects.filter(
        is_active=False, start_datetime__lte=now
    ).exclude(end_datetime__lt=now)
    activated = to_activate.update(is_active=True)

    # Deactivate slides past their end time
    to_deactivate = HeroSlide.objects.filter(is_active=True, end_datetime__lt=now)
    deactivated = to_deactivate.update(is_active=False)

    if activated or deactivated:
        logger.info("Hero slides: activated=%d, deactivated=%d", activated, deactivated)


@shared_task
def activate_scheduled_announcement_bars():
    """
    Runs every 15 minutes.
    Activates/deactivates announcement bars by schedule.
    """
    from .models import AnnouncementBar

    now = timezone.now()

    to_activate = AnnouncementBar.objects.filter(
        is_active=False, start_datetime__lte=now
    ).exclude(end_datetime__lt=now)
    activated = to_activate.update(is_active=True)

    to_deactivate = AnnouncementBar.objects.filter(is_active=True, end_datetime__lt=now)
    deactivated = to_deactivate.update(is_active=False)

    if activated or deactivated:
        logger.info("Announcement bars: activated=%d, deactivated=%d", activated, deactivated)
