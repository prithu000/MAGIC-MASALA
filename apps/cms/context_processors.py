"""apps/cms/context_processors.py — active announcement bar for every template."""

from django.utils import timezone


def announcement_bar(request):
    from .models import AnnouncementBar

    now = timezone.now()
    bars = list(
        AnnouncementBar.objects.filter(is_active=True)
        .exclude(end_datetime__lt=now)
        .exclude(start_datetime__gt=now)
        .order_by("display_order", "id")
    )
    return {
        "announcement_bars": bars,
        "announcement_bar": bars[0] if bars else None,
    }

