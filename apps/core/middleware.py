"""
apps/core/middleware.py — Production security headers middleware.
Provides Content-Security-Policy (CSP) and Permissions-Policy headers.
"""

from django.conf import settings


class SecurityHeadersMiddleware:
    """
    Appends Content-Security-Policy and Permissions-Policy headers
    tuned for the MU Magic Masala storefront, Razorpay, Google Fonts, and Alpine.js.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Set modern Permissions-Policy to disable unnecessary browser APIs
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=(self 'https://checkout.razorpay.com')",
        )

        # Set Content-Security-Policy if not DEBUG or explicitly enabled
        enable_csp = getattr(settings, "ENABLE_CSP", False) or not settings.DEBUG
        if enable_csp:
            csp_directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://unpkg.com https://checkout.razorpay.com https://accounts.google.com",
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.tailwindcss.com https://accounts.google.com",
                "font-src 'self' https://fonts.gstatic.com data:",
                "img-src 'self' data: blob: https: http: https://*.googleusercontent.com",
                "connect-src 'self' https://api.postalpincode.in https://lumberjack.razorpay.com https://*.razorpay.com https://accounts.google.com https://oauth2.googleapis.com https://www.googleapis.com",
                "frame-src 'self' https://api.razorpay.com https://checkout.razorpay.com https://accounts.google.com",
                "object-src 'none'",
                "base-uri 'self'",
                "form-action 'self' https://api.razorpay.com https://accounts.google.com",
            ]
            response.headers.setdefault("Content-Security-Policy", "; ".join(csp_directives))

        return response
