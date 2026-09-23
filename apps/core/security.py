"""
apps/core/security.py — Production security utilities: rate limiting, safe redirects, and validation.
"""

import functools
import hashlib
import time
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme


def get_client_ip(request) -> str:
    """Extract real client IP address considering reverse proxies."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "")
    return ip or "127.0.0.1"


def ratelimit(rate="10/m", key="ip", block=True):
    """
    Cache-based rate limiting decorator.
    `rate`: e.g. "5/m" (5 per minute), "20/h" (20 per hour), "100/d" (100 per day).
    `key`: 'ip', 'user_or_ip', or callable(request).
    Works with any cache backend (Redis, LocMem, etc.).
    """
    count, unit = rate.split("/")
    max_requests = int(count)
    seconds_map = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    window_seconds = seconds_map.get(unit.lower(), 60)

    def decorator(view_func):
        @functools.wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if key == "ip":
                identifier = get_client_ip(request)
            elif key == "user_or_ip":
                if request.user.is_authenticated:
                    identifier = f"user_{request.user.pk}"
                else:
                    identifier = f"ip_{get_client_ip(request)}"
            elif callable(key):
                identifier = key(request)
            else:
                identifier = get_client_ip(request)

            view_name = view_func.__name__
            cache_key = f"rl:{view_name}:{identifier}"

            # Sliding / fixed window in cache
            current = cache.get(cache_key, 0)
            if current >= max_requests:
                if block:
                    if (
                        request.headers.get("X-Requested-With") == "XMLHttpRequest"
                        or request.content_type == "application/json"
                        or request.path.startswith("/api/")
                    ):
                        return JsonResponse(
                            {
                                "error": "Too many requests. Please slow down and try again later.",
                                "rate_limited": True,
                            },
                            status=429,
                        )
                    return HttpResponse(
                        "Too many requests. Please wait a moment before trying again.",
                        status=429,
                        content_type="text/plain",
                    )
            else:
                # Increment counter
                try:
                    cache.incr(cache_key)
                except ValueError:
                    cache.set(cache_key, 1, window_seconds)

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def safe_redirect(request, target_url, fallback="cms:home"):
    """Validates that target_url is safe and belongs to allowed hosts to prevent open redirects."""
    allowed_hosts = {request.get_host()}
    if url_has_allowed_host_and_scheme(target_url, allowed_hosts=allowed_hosts, require_https=request.is_secure()):
        return redirect(target_url)
    return redirect(fallback)
